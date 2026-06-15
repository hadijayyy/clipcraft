"""Audio extraction and transcription with faster-whisper"""
import os
import json
import subprocess
import numpy as np
import tempfile

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")

os.makedirs(AUDIO_DIR, exist_ok=True)

# Whisper model singleton — load once, reuse across requests
_whisper_model = None


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _whisper_model


def get_youtube_stream_url(url: str) -> str:
    """Get direct stream URL from YouTube via Opencode Go API.
    Falls back to yt-dlp if Opencode fails."""
    try:
        from processing.opencode import get_youtube_stream_url as opencode_get
        return opencode_get(url)
    except Exception as e:
        print(f"[Opencode] Import failed: {e}, using yt-dlp fallback")

    # Fallback: yt-dlp
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
    return ""


def extract_audio_from_url(url: str, audio_id: str) -> str:
    """Extract audio directly from YouTube URL (no full video download)"""
    audio_path = os.path.join(AUDIO_DIR, f"{audio_id}.wav")
    if os.path.exists(audio_path):
        return audio_path

    # Get stream URL
    stream_url = get_youtube_stream_url(url)
    if not stream_url:
        raise RuntimeError(
            "YouTube blocked the request (bot detection). "
            "Try: 1) Upload video file directly instead of URL, "
            "or 2) Provide cookies.txt file for authentication."
        )

    # Extract audio directly from stream
    cmd = [
        "ffmpeg", "-y",
        "-i", stream_url,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=600)
    return audio_path


def get_youtube_duration(url: str) -> float:
    """Get video duration from YouTube URL without downloading"""
    cmd = [
        "yt-dlp",
        "--get-duration",
        "--no-playlist",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        duration_str = result.stdout.strip()
        # Parse HH:MM:SS or seconds
        parts = duration_str.split(':')
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(parts[0])
    return 0

def extract_audio(video_path: str, audio_id: str) -> str:
    """Extract audio from video file using FFmpeg"""
    audio_path = os.path.join(AUDIO_DIR, f"{audio_id}.wav")
    if os.path.exists(audio_path):
        return audio_path
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=600)
    return audio_path

def transcribe(audio_path: str, audio_id: str) -> dict:
    """Transcribe audio using faster-whisper. Returns transcript JSON."""
    transcript_path = os.path.join(AUDIO_DIR, f"{audio_id}_transcript.json")
    if os.path.exists(transcript_path):
        with open(transcript_path) as f:
            return json.load(f)

    try:
        model = _get_whisper_model()
        segments, info = model.transcribe(audio_path, language="en")
        
        result = {
            "language": info.language,
            "duration": info.duration,
            "segments": []
        }
        for seg in segments:
            result["segments"].append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip()
            })
        
        with open(transcript_path, "w") as f:
            json.dump(result, f)
        return result
    except Exception as e:
        return {"error": str(e), "segments": []}

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0

def get_video_info(video_path: str) -> dict:
    """Get video dimensions and info"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,r_frame_rate",
        "-of", "json",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        streams = data.get("streams", [{}])
        if streams:
            s = streams[0]
            fps_parts = s.get("r_frame_rate", "30/1").split("/")
            fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30
            return {
                "width": int(s.get("width", 1920)),
                "height": int(s.get("height", 1080)),
                "codec": s.get("codec_name", "h264"),
                "fps": round(fps, 2)
            }
    return {"width": 1920, "height": 1080, "codec": "h264", "fps": 30}
