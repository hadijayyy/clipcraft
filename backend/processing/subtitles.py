"""SRT subtitle generation from transcript segments"""
import json
import os

def segments_to_srt(segments: list) -> str:
    """Convert transcript segments to SRT format"""
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start = _format_srt_time(seg["start"])
        end = _format_srt_time(seg["end"])
        text = seg.get("text", "").strip()
        if text:
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")
    return "\n".join(srt_lines)

def _format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def segments_to_vtt(segments: list) -> str:
    """Convert to WebVTT format"""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = _format_vtt_time(seg["start"])
        end = _format_vtt_time(seg["end"])
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
    return "\n".join(lines)

def _format_vtt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def save_srt(segments: list, output_path: str):
    """Save SRT to file"""
    content = segments_to_srt(segments)
    with open(output_path, "w") as f:
        f.write(content)
    return output_path
