"""Opencode Go API client — get direct YouTube stream URLs without yt-dlp"""
import os
import json
import subprocess
import tempfile

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Opencode Go API config
OPENCODE_API_URL = os.getenv("OPENCODE_API_URL", "https://opencode.ai/zen/go/v1/youtube")
OPENCODE_API_KEY=os.getenv("OPENCODE_API_KEY", "")


def get_youtube_stream_url(url: str) -> str:
    """Get direct stream URL from YouTube via Opencode Go API.
    Falls back to yt-dlp if Opencode fails."""
    # Try Opencode Go API first
    if OPENCODE_API_KEY:
        try:
            import requests
            resp = requests.get(
                OPENCODE_API_URL,
                params={"url": url, "apikey": OPENCODE_API_KEY},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                stream_url = (
                    data.get("result", {}).get("videoUrl")
                    or data.get("download_link")
                    or ""
                )
                if stream_url:
                    print(f"[Opencode Go] Got stream URL for {url[:50]}...")
                    return stream_url
        except Exception as e:
            print(f"[Opencode Go] Error: {e}, falling back to yt-dlp")

    # Fallback: yt-dlp (may fail on VPS due to bot detection)
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "--get-url",
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and result.stdout.strip():
        urls = [u for u in result.stdout.strip().split('\n') if u.startswith('http')]
        return urls[0] if urls else ""

    print(f"[yt-dlp] Failed: {result.stderr.strip()[:200]}")
    return ""


def extract_audio_from_url(url: str, audio_id: str) -> str:
    """Extract audio directly from YouTube URL via Opencode Go stream."""
    audio_path = os.path.join(AUDIO_DIR, f"{audio_id}.wav")
    if os.path.exists(audio_path):
        return audio_path

    stream_url = get_youtube_stream_url(url)
    if not stream_url:
        raise RuntimeError(
            "YouTube blocked the request. "
            "Set OPENCODE_API_KEY environment variable to use Opencode Go API, "
            "or upload video file directly."
        )

    cmd = [
        "ffmpeg", "-y",
        "-i", stream_url,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=600)
    if result.returncode != 0 or not os.path.exists(audio_path):
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr[-300:]}")
    return audio_path


def get_youtube_duration(url: str) -> float:
    """Get video duration from YouTube URL without downloading.
    Uses Opencode Go API if available, otherwise yt-dlp."""
    # Try yt-dlp first (duration usually works even with bot detection)
    cmd = [
        "yt-dlp",
        "--get-duration",
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        duration_str = result.stdout.strip()
        parts = duration_str.split(':')
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            else:
                return float(parts[0])
        except (ValueError, IndexError):
            return 0
    return 0


def create_clip_from_stream(
    stream_url: str,
    output_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 720,
    target_height: int = 1280
) -> str:
    """Create a vertical 9:16 clip directly from a stream URL.
    Downloads ONLY the segment needed, not the full video."""
    duration = end_time - start_time
    if duration <= 0:
        raise ValueError(f"Invalid clip duration: {duration}s")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", stream_url,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-vf", (
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black"
        ),
        "-c:a", "aac",
        "-b:a", "128k",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg clip failed: {result.stderr[-500:]}")
    return output_path


def create_clip_from_youtube(
    youtube_url: str,
    output_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 720,
    target_height: int = 1280
) -> str:
    """Create clip directly from YouTube URL via Opencode Go API.
    Only downloads the needed segment, not the full video."""
    stream_url = get_youtube_stream_url(youtube_url)
    if not stream_url:
        raise RuntimeError("Could not get stream URL from YouTube")
    return create_clip_from_stream(
        stream_url, output_path, start_time, end_time, target_width, target_height
    )
