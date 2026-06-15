"""Audio extraction and transcription with faster-whisper"""
import os
import json
import subprocess
import numpy as np

STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")

os.makedirs(AUDIO_DIR, exist_ok=True)

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
        from faster_whisper import WhisperModel
        model = WhisperModel("base", device="cpu", compute_type="int8")
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
        import json as j
        data = j.loads(result.stdout)
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
        import json as j
        data = j.loads(result.stdout)
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
