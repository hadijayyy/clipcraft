"""FFmpeg-based video clipping with vertical 9:16 crop and blurred background"""
import os
import subprocess
import json
from processing.transcriber import get_youtube_stream_url

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
CLIPS_DIR = os.path.join(STORAGE_DIR, "clips")
os.makedirs(CLIPS_DIR, exist_ok=True)


def create_vertical_clip_from_url(
    stream_url: str,
    output_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 720,
    target_height: int = 1280
) -> str:
    """Create a vertical 9:16 clip directly from a stream URL (YouTube) without downloading full video.
    Uses -ss before -i for fast seeking."""
    
    # For streaming URLs, we use -ss before -i for fast seeking
    # and download only the needed segment
    duration = end_time - start_time
    
    # Simple approach: download segment, crop to vertical
    # Use -ss (start) and -t (duration) for minimal download
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", stream_url,
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-vf", f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return output_path


def create_vertical_clip_from_youtube(
    youtube_url: str,
    output_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 720,
    target_height: int = 1280
) -> str:
    """Create clip directly from YouTube URL without downloading full video."""
    stream_url = get_youtube_stream_url(youtube_url)
    if not stream_url:
        return ""
    return create_vertical_clip_from_url(stream_url, output_path, start_time, end_time, target_width, target_height)


def create_vertical_clip(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 720,
    target_height: int = 1280
) -> str:
    """Create a vertical 9:16 clip with blurred background.
    Uses smart crop — keeps the center region when source is wider than 9:16.
    Adds blurred background padding when source is narrower."""
    
    # Get source dimensions
    cmd_probe = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        input_path
    ]
    result = subprocess.run(cmd_probe, capture_output=True, text=True, timeout=30)
    info = json.loads(result.stdout)
    streams = info.get("streams", [{}])
    src_w = int(streams[0].get("width", 1920))
    src_h = int(streams[0].get("height", 1080))
    
    src_aspect = src_w / src_h
    target_aspect = target_width / target_height  # 720/1280 = 0.5625
    
    clip_duration = end_time - start_time
    
    # Filter complex untuk vertical + blurred background
    if src_aspect > target_aspect:
        # Source lebih lebar dari 9:16 — crop tengah
        crop_w = int(src_h * target_aspect)
        crop_x = int((src_w - crop_w) / 2)
        # Pastikan genap (ffmpeg requirement)
        if crop_w % 2 != 0: crop_w += 1
        if crop_x % 2 != 0: crop_x += 1
        
        filter_chain = (
            f"[0:v]trim={start_time}:{end_time},setpts=PTS-STARTPTS,"
            f"crop={crop_w}:{src_h}:{crop_x}:0,scale={target_width}:{target_height}[v]"
        )
    else:
        # Source lebih sempit dari 9:16 — pad with blurred bg
        # Scale source to fill width
        scale_h = int(target_width / src_aspect)
        filter_chain = (
            f"[0:v]trim={start_time}:{end_time},setpts=PTS-STARTPTS,"
            f"split[original][blur];"
            f"[blur]scale={target_width}:{target_height},boxblur=10:5[bg];"
            f"[original]scale={target_width}:{scale_h}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter_complex", filter_chain,
        "-map", "[v]",
        "-map", "0:a?" if src_aspect > target_aspect else "-an",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    # If source is wider, include audio too
    if src_aspect > target_aspect:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-filter_complex", filter_chain,
            "-map", "[v]",
            "-map", "0:a",
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            output_path
        ]
    
    subprocess.run(cmd, capture_output=True, timeout=600)
    return output_path

def create_auto_clips(video_path: str, moments: list, video_id: int) -> list:
    """Create clips for all detected moments"""
    clips = []
    for i, moment in enumerate(moments[:10]):  # max 10 auto clips
        output = os.path.join(CLIPS_DIR, f"clip_{video_id}_{i}.mp4")
        create_vertical_clip(
            video_path, output,
            moment["start"], moment["end"]
        )
        clips.append({
            "path": output,
            "start": moment["start"],
            "end": moment["end"],
            "text": moment["text"]
        })
    return clips

def create_manual_clip(video_path: str, start: float, end: float, video_id: int) -> str:
    """Create a single manual clip"""
    output = os.path.join(CLIPS_DIR, f"clip_{video_id}_manual_{int(start)}.mp4")
    return create_vertical_clip(video_path, output, start, end)

def create_split_clips(video_path: str, duration: float, target_length: int, overlap: float, video_id: int) -> list:
    """Split video into segments of target_length with overlap"""
    clips = []
    start = 0
    step = target_length - overlap
    i = 0
    
    while start < duration:
        end = min(start + target_length, duration)
        if end - start < 5:  # Skip segments shorter than 5s
            break
        output = os.path.join(CLIPS_DIR, f"clip_{video_id}_split_{i}.mp4")
        create_vertical_clip(video_path, output, start, end)
        clips.append({
            "path": output,
            "start": start,
            "end": end
        })
        start += step
        i += 1
    
    return clips
