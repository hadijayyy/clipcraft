"""Smart Video Cropper — YOLOv8 content-aware cropping + scene detection.
Merged from AutoCrop-Vertical (kamilstanuch) into ClipCraft.
Converts horizontal videos to vertical 9:16 with intelligent subject tracking."""

import os
import subprocess
import json
import tempfile
import cv2
import numpy as np

# YOLO model (lazy load)
_yolo_model = None


def _get_yolo():
    global _yolo_model
    if _yolo_model is None:
        from ultralytics import YOLO
        model_path = os.path.join(os.path.dirname(__file__), '..', 'storage', 'yolov8n.pt')
        _yolo_model = YOLO(model_path)
    return _yolo_model


def detect_scenes(video_path: str, threshold: float = 27.0) -> list:
    """Detect scene boundaries using PySceneDetect ContentDetector."""
    try:
        from scenedetect import open_video, SceneManager
        from scenedetect.detectors import ContentDetector

        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        scene_manager.detect_scenes(video)
        scene_list = scene_manager.get_scene_list()

        scenes = []
        for i, (start, end) in enumerate(scene_list):
            scenes.append({
                'index': i,
                'start': start.get_seconds(),
                'end': end.get_seconds(),
                'duration': end.get_seconds() - start.get_seconds()
            })
        return scenes
    except Exception as e:
        print(f"[SmartCrop] Scene detection failed: {e}, using full video")
        # Fallback: treat whole video as one scene
        duration = get_video_duration(video_path)
        return [{'index': 0, 'start': 0, 'end': duration, 'duration': duration}]


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode == 0:
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0


def get_video_info(video_path: str) -> dict:
    """Get video dimensions and info."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,r_frame_rate",
        "-of", "json", video_path
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
                'width': int(s.get("width", 1920)),
                'height': int(s.get("height", 1080)),
                'codec': s.get("codec_name", "h264"),
                'fps': round(fps, 2)
            }
    return {'width': 1920, 'height': 1080, 'codec': 'h264', 'fps': 30}


def analyze_scene(video_path: str, scene_start: float, scene_end: float) -> dict:
    """Analyze a scene for people/faces using YOLOv8.
    Returns detection results and cropping strategy."""
    model = _get_yolo()

    # Extract middle frame of scene
    mid_time = (scene_start + scene_end) / 2
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, mid_time * 1000)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return {'strategy': 'LETTERBOX', 'reason': 'Could not read frame'}

    h, w = frame.shape[:2]
    target_aspect = 9 / 16
    src_aspect = w / h

    # Run YOLO detection
    results = model(frame, verbose=False)

    # Find person detections (class 0 = person)
    persons = []
    for r in results:
        for box in r.boxes:
            if int(box.cls[0]) == 0:  # person class
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                persons.append({
                    'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                    'cx': (x1 + x2) / 2,
                    'cy': (y1 + y2) / 2,
                    'width': x2 - x1,
                    'height': y2 - y1,
                    'confidence': float(box.conf[0])
                })

    if not persons:
        return {
            'strategy': 'LETTERBOX',
            'reason': 'No people detected',
            'persons': []
        }

    # Calculate group bounding box
    group_x1 = min(p['x1'] for p in persons)
    group_y1 = min(p['y1'] for p in persons)
    group_x2 = max(p['x2'] for p in persons)
    group_y2 = max(p['y2'] for p in persons)
    group_width = group_x2 - group_x1
    group_center_x = (group_x1 + group_x2) / 2

    # Check if group fits in vertical crop
    crop_width = h * target_aspect
    fits_vertically = group_width <= crop_width * 0.95

    if len(persons) == 1:
        # Single person: track their center
        p = persons[0]
        return {
            'strategy': 'TRACK',
            'reason': f'Single person detected (conf: {p["confidence"]:.2f})',
            'track_x': p['cx'],
            'track_y': p['cy'],
            'persons': persons
        }
    elif fits_vertically:
        # Multiple people that fit: track group center
        return {
            'strategy': 'TRACK',
            'reason': f'{len(persons)} people fit in vertical crop',
            'track_x': group_center_x,
            'track_y': (group_y1 + group_y2) / 2,
            'persons': persons
        }
    else:
        # Multiple people that don't fit: letterbox
        return {
            'strategy': 'LETTERBOX',
            'reason': f'{len(persons)} people too wide for vertical crop',
            'persons': persons
        }


def smart_crop_video(
    input_path: str,
    output_path: str,
    start_time: float = None,
    end_time: float = None,
    target_width: int = 720,
    target_height: int = 1280,
    quality: str = 'balanced',
    verbose: bool = False
) -> str:
    """Smart crop a video to vertical 9:16 using YOLOv8 content detection.

    Pipeline:
    1. Detect scenes
    2. Analyze each scene for people/faces
    3. Apply TRACK (crop on subject) or LETTERBOX (scale + black bars)
    4. Output final vertical video with original audio
    """
    info = get_video_info(input_path)
    src_w, src_h = info['width'], info['height']
    src_aspect = src_w / src_h
    target_aspect = target_width / target_height

    # Determine time range
    if start_time is None:
        start_time = 0
    if end_time is None:
        end_time = get_video_duration(input_path)

    if verbose:
        print(f"[SmartCrop] Input: {src_w}x{src_h}, Target: {target_width}x{target_height}")
        print(f"[SmartCrop] Time: {start_time:.1f}s - {end_time:.1f}s")

    # Step 1: Detect scenes
    scenes = detect_scenes(input_path)
    # Filter scenes within time range
    scenes = [s for s in scenes if s['end'] > start_time and s['start'] < end_time]
    if verbose:
        print(f"[SmartCrop] Found {len(scenes)} scenes in range")

    # Step 2: Analyze each scene
    scene_analyses = []
    for scene in scenes:
        analysis = analyze_scene(input_path, scene['start'], scene['end'])
        analysis['scene'] = scene
        scene_analyses.append(analysis)
        if verbose:
            print(f"  Scene {scene['index']}: {analysis['strategy']} — {analysis['reason']}")

    # Step 3: Build FFmpeg filter complex
    # For simplicity: use uniform strategy across the clip
    # (most scenes will have same strategy in a short clip)
    strategies = [a['strategy'] for a in scene_analyses]
    track_count = strategies.count('TRACK')

    if track_count > len(strategies) / 2:
        # Majority TRACK: crop centered on detected subjects
        # Find average track position
        track_positions = [a.get('track_x', src_w / 2) for a in scene_analyses if a['strategy'] == 'TRACK']
        avg_track_x = sum(track_positions) / len(track_positions) if track_positions else src_w / 2

        # Calculate crop region
        crop_w = int(src_h * target_aspect)
        crop_x = int(max(0, min(src_w - crop_w, avg_track_x - crop_w / 2)))
        if crop_x % 2 != 0:
            crop_x += 1

        filter_complex = (
            f"[0:v]crop={crop_w}:{src_h}:{crop_x}:0,"
            f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
            f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black[v]"
        )
        strategy_used = 'TRACK'
    else:
        # Majority LETTERBOX: scale with blurred background
        filter_complex = (
            f"[0:v]split[original][blur];"
            f"[blur]scale={target_width}:{target_height},boxblur=20:5[bg];"
            f"[original]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2[v]"
        )
        strategy_used = 'LETTERBOX'

    # Step 4: Encode
    quality_presets = {
        'fast': ['-crf', '28', '-preset', 'veryfast'],
        'balanced': ['-crf', '23', '-preset', 'fast'],
        'high': ['-crf', '18', '-preset', 'slow'],
    }
    encode_args = quality_presets.get(quality, quality_presets['balanced'])

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-to", str(end_time),
        "-i", input_path,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        *encode_args,
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path
    ]

    if verbose:
        print(f"[SmartCrop] Encoding with {strategy_used} strategy...")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")

    return output_path


def smart_crop_clip(
    input_path: str,
    output_path: str,
    start_time: float,
    end_time: float,
    target_width: int = 720,
    target_height: int = 1280,
    quality: str = "balanced"
) -> str:
    """Convenience wrapper for clipping a segment with smart cropping."""
    return smart_crop_video(
        input_path, output_path,
        start_time=start_time, end_time=end_time,
        target_width=target_width, target_height=target_height,
        quality=quality, verbose=False
    )
