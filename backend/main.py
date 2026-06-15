"""ClipCraft API — FastAPI backend"""
import os
import json
import uuid
import subprocess
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from models.database import init_db, get_db, Video, Clip, StyleExample
from processing.transcriber import extract_audio, transcribe, get_video_duration, get_video_info, extract_audio_from_url, get_youtube_duration
from processing.analyzer import analyze_moments, get_hooks
from processing.clipper import create_vertical_clip, create_split_clips, create_vertical_clip_from_youtube
from processing.subtitles import segments_to_srt, save_srt
from processing.style_learner import save_style, load_all_styles, delete_style, learn_from_example

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
VIDEOS_DIR = os.path.join(STORAGE_DIR, "videos")
CLIPS_DIR = os.path.join(STORAGE_DIR, "clips")
THUMBS_DIR = os.path.join(STORAGE_DIR, "thumbnails")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")

for d in [STORAGE_DIR, VIDEOS_DIR, CLIPS_DIR, THUMBS_DIR, AUDIO_DIR]:
    os.makedirs(d, exist_ok=True)

app = FastAPI(title="ClipCraft API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

# ─── Health ───────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

# ─── Video Upload ─────────────────────────────────────────
@app.post("/api/upload")
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    video_id = str(uuid.uuid4())[:8]
    filename = f"{video_id}{ext}"
    filepath = os.path.join(VIDEOS_DIR, filename)
    
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    
    duration = get_video_duration(filepath)
    
    video = Video(
        filename=filename,
        original_name=file.filename,
        source="upload",
        duration=duration,
        status="uploaded"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    return {"id": video.id, "filename": filename, "original_name": file.filename, "duration": duration, "status": "uploaded"}

# ─── YouTube Import ───────────────────────────────────────
@app.post("/api/youtube")
async def import_youtube(url: str = Form(...), db: Session = Depends(get_db)):
    video_id = str(uuid.uuid4())[:8]
    filename = f"{video_id}.mp4"
    filepath = os.path.join(VIDEOS_DIR, filename)
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", filepath,
        "--no-playlist",
        "--merge-output-format", "mp4",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    
    if result.returncode != 0 or not os.path.exists(filepath):
        # Fallback to any format
        cmd = ["yt-dlp", "-f", "best", "-o", filepath, "--no-playlist", url]
        subprocess.run(cmd, capture_output=True, timeout=600)
    
    if not os.path.exists(filepath):
        raise HTTPException(500, "Failed to download YouTube video")
    
    duration = get_video_duration(filepath)
    
    video = Video(
        filename=filename,
        original_name=f"YouTube - {url[:50]}",
        source="youtube",
        source_url=url,
        duration=duration,
        status="uploaded"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    return {"id": video.id, "filename": filename, "duration": duration, "status": "uploaded"}

# ─── YouTube Direct Link (no full download) ─────────────
@app.post("/api/youtube-direct")
async def youtube_direct(url: str = Form(...), db: Session = Depends(get_db)):
    """Import YouTube video without downloading full file.
    Only downloads audio for transcription. Clips are made directly from URL."""
    video_id = str(uuid.uuid4())[:8]
    
    # Get duration from URL (no download)
    duration = get_youtube_duration(url)
    
    video = Video(
        filename=f"{video_id}_stream",
        original_name=f"YouTube Direct - {url[:50]}",
        source="youtube_direct",
        source_url=url,
        duration=duration,
        status="uploaded"
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    
    return {"id": video.id, "duration": duration, "status": "uploaded", "mode": "direct"}

# ─── Process Direct YouTube (audio only) ────────────────
@app.post("/api/process-direct/{video_id}")
def process_direct_youtube(video_id: int, db: Session = Depends(get_db)):
    """Process YouTube video directly — only downloads audio, not full video."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    if not video.source_url:
        raise HTTPException(400, "No YouTube URL found")
    
    video.status = "processing"
    db.commit()
    
    try:
        # 1. Extract audio directly from URL (small download)
        audio_path = extract_audio_from_url(video.source_url, str(video.id))
        if not audio_path or not os.path.exists(audio_path):
            raise Exception("Failed to extract audio from URL")
        
        # 2. Transcribe
        transcript = transcribe(audio_path, str(video.id))
        
        # 3. Analyze for moments
        moments = analyze_moments(transcript)
        hooks = get_hooks(transcript)
        
        video.transcription = json.dumps(transcript)
        video.moments_json = json.dumps({"moments": moments, "hooks": hooks})
        video.status = "ready"
        db.commit()
        
        return {
            "status": "ready",
            "transcript": transcript,
            "moments": moments,
            "hooks": hooks
        }
    except Exception as e:
        video.status = "error"
        db.commit()
        raise HTTPException(500, str(e))

# ─── Clip Direct from YouTube URL ──────────────────────
@app.post("/api/clip-direct/{video_id}")
def clip_direct_from_youtube(
    video_id: int,
    start: float = Form(...),
    end: float = Form(...),
    db: Session = Depends(get_db)
):
    """Create clip directly from YouTube URL — no full video download."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    if not video.source_url:
        raise HTTPException(400, "No YouTube URL found")
    
    output = os.path.join(CLIPS_DIR, f"clip_{video_id}_direct_{uuid.uuid4()[:6]}.mp4")
    
    try:
        create_vertical_clip_from_youtube(video.source_url, output, start, end)
        
        clip = Clip(
            video_id=video_id, clip_path=output,
            start_time=start, end_time=end,
            mode="direct"
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        
        return {"id": clip.id, "path": output, "start": start, "end": end}
    except Exception as e:
        raise HTTPException(500, f"Failed to create clip: {str(e)}")

# ─── Process (Transcribe + Analyze) ───────────────────────
@app.post("/api/process/{video_id}")
def process_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    video.status = "processing"
    db.commit()
    
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Video file not found on disk")
    
    try:
        # 1. Extract audio
        audio_path = extract_audio(filepath, str(video.id))
        
        # 2. Transcribe
        transcript = transcribe(audio_path, str(video.id))
        
        # 3. Analyze for moments
        moments = analyze_moments(transcript)
        hooks = get_hooks(transcript)
        
        video.transcription = json.dumps(transcript)
        video.moments_json = json.dumps({"moments": moments, "hooks": hooks})
        video.status = "ready"
        db.commit()
        
        return {
            "status": "ready",
            "transcript": transcript,
            "moments": moments,
            "hooks": hooks
        }
    except Exception as e:
        video.status = "error"
        db.commit()
        raise HTTPException(500, str(e))

# ─── Video Library ────────────────────────────────────────
@app.get("/api/videos")
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.created_at.desc()).all()
    return [
        {
            "id": v.id,
            "original_name": v.original_name,
            "source": v.source,
            "duration": v.duration,
            "status": v.status,
            "created_at": str(v.created_at),
            "has_transcript": bool(v.transcription)
        }
        for v in videos
    ]

@app.get("/api/videos/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    result = {
        "id": video.id,
        "filename": video.filename,
        "original_name": video.original_name,
        "source": video.source,
        "source_url": video.source_url,
        "duration": video.duration,
        "status": video.status,
        "created_at": str(video.created_at),
        "transcript": json.loads(video.transcription) if video.transcription else None,
        "moments": json.loads(video.moments_json) if video.moments_json else None,
    }
    return result

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Delete clips
    clips = db.query(Clip).filter(Clip.video_id == video_id).all()
    for clip in clips:
        if os.path.exists(clip.clip_path):
            os.remove(clip.clip_path)
        if clip.thumbnail_path and os.path.exists(clip.thumbnail_path):
            os.remove(clip.thumbnail_path)
        db.delete(clip)
    
    # Delete video file
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    db.delete(video)
    db.commit()
    return {"status": "deleted"}

@app.get("/api/video/{video_id}/stream")
def stream_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found on disk")
    return FileResponse(filepath, media_type="video/mp4")

# ─── Clipping ─────────────────────────────────────────────
@app.post("/api/clip/auto/{video_id}")
def auto_clip(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    if not video.moments_json:
        raise HTTPException(400, "Process video first (transcribe + analyze)")
    
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Video file not found")
    
    data = json.loads(video.moments_json)
    moments = sorted(data.get("moments", []), key=lambda x: x["score"], reverse=True)[:10]
    
    clips = []
    for i, m in enumerate(moments):
        output = os.path.join(CLIPS_DIR, f"clip_{video_id}_auto_{i}.mp4")
        try:
            create_vertical_clip(filepath, output, m["start"], m["end"])
            clip = Clip(
                video_id=video_id, clip_path=output,
                start_time=m["start"], end_time=m["end"],
                mode="auto"
            )
            db.add(clip)
            db.commit()
            db.refresh(clip)
            clips.append({"id": clip.id, "start": m["start"], "end": m["end"], "path": output, "text": m["text"]})
        except Exception as e:
            continue
    
    return {"clips": clips, "count": len(clips)}

@app.post("/api/clip/manual/{video_id}")
def manual_clip(video_id: int, start: float = Form(...), end: float = Form(...), db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    output = os.path.join(CLIPS_DIR, f"clip_{video_id}_manual_{uuid.uuid4()[:6]}.mp4")
    
    create_vertical_clip(filepath, output, start, end)
    
    clip = Clip(
        video_id=video_id, clip_path=output,
        start_time=start, end_time=end,
        mode="manual"
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)
    
    return {"id": clip.id, "path": output, "start": start, "end": end}

@app.post("/api/clip/split/{video_id}")
def split_clip(video_id: int, target_length: int = Form(30), overlap: float = Form(0.5), db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    duration = video.duration or get_video_duration(filepath)
    
    clips = []
    start = 0
    step = target_length - overlap
    i = 0
    
    while start < duration:
        end = min(start + target_length, duration)
        if end - start < 5:
            break
        output = os.path.join(CLIPS_DIR, f"clip_{video_id}_split_{i}.mp4")
        try:
            create_vertical_clip(filepath, output, start, end)
            clip = Clip(
                video_id=video_id, clip_path=output,
                start_time=start, end_time=end,
                mode="split"
            )
            db.add(clip)
            db.commit()
            db.refresh(clip)
            clips.append({"id": clip.id, "path": output, "start": start, "end": end})
        except Exception as e:
            continue
        start += step
        i += 1
    
    return {"clips": clips, "count": len(clips)}

# ─── Clips ────────────────────────────────────────────────
@app.get("/api/clips/{video_id}")
def list_clips(video_id: int, db: Session = Depends(get_db)):
    clips = db.query(Clip).filter(Clip.video_id == video_id).all()
    return [
        {
            "id": c.id,
            "video_id": c.video_id,
            "start": c.start_time,
            "end": c.end_time,
            "mode": c.mode,
            "has_thumbnail": bool(c.thumbnail_path),
            "created_at": str(c.created_at)
        }
        for c in clips
    ]

@app.get("/api/clip/{clip_id}")
def get_clip(clip_id: int, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    return {
        "id": clip.id,
        "video_id": clip.video_id,
        "clip_path": clip.clip_path,
        "thumbnail_path": clip.thumbnail_path,
        "start": clip.start_time,
        "end": clip.end_time,
        "mode": clip.mode,
        "subtitles": clip.subtitles_json,
        "overlays": clip.overlays_json,
    }

@app.get("/api/clip/{clip_id}/stream")
def stream_clip(clip_id: int, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    if not os.path.exists(clip.clip_path):
        raise HTTPException(404, "Clip file not found")
    return FileResponse(clip.clip_path, media_type="video/mp4")

@app.get("/api/clip/{clip_id}/srt")
def get_clip_srt(clip_id: int, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    
    video = db.query(Video).filter(Video.id == clip.video_id).first()
    if not video or not video.transcription:
        raise HTTPException(400, "No transcript available")
    
    transcript = json.loads(video.transcription)
    segments = transcript.get("segments", [])
    
    # Filter segments within clip time range
    clip_segments = [
        s for s in segments
        if s["end"] >= clip.start_time and s["start"] <= clip.end_time
    ]
    # Adjust times relative to clip
    for s in clip_segments:
        s["start"] = max(0, s["start"] - clip.start_time)
        s["end"] = min(clip.end_time - clip.start_time, s["end"] - clip.start_time)
    
    srt_content = segments_to_srt(clip_segments)
    return JSONResponse({"srt": srt_content, "segments": clip_segments})

@app.post("/api/clip/{clip_id}/subtitles")
def save_clip_subtitles(clip_id: int, subtitles: str = Form(...), db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    clip.subtitles_json = subtitles
    db.commit()
    return {"status": "saved"}

@app.post("/api/clip/{clip_id}/overlays")
def save_clip_overlays(clip_id: int, overlays: str = Form(...), db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    clip.overlays_json = overlays
    db.commit()
    return {"status": "saved"}

@app.delete("/api/clip/{clip_id}")
def delete_clip(clip_id: int, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    if os.path.exists(clip.clip_path):
        os.remove(clip.clip_path)
    db.delete(clip)
    db.commit()
    return {"status": "deleted"}

# ─── Thumbnail ────────────────────────────────────────────
@app.post("/api/thumbnail/{clip_id}")
def generate_thumbnail(clip_id: int, time_sec: float = Form(0.5), db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    
    thumb_path = os.path.join(THUMBS_DIR, f"thumb_{clip_id}.jpg")
    cmd = [
        "ffmpeg", "-y",
        "-i", clip.clip_path,
        "-ss", str(time_sec),
        "-vframes", "1",
        "-q:v", "2",
        thumb_path
    ]
    subprocess.run(cmd, capture_output=True, timeout=30)
    
    clip.thumbnail_path = thumb_path
    db.commit()
    
    return {"thumbnail_path": thumb_path}

@app.get("/api/thumbnail/{clip_id}/image")
def get_thumbnail(clip_id: int, db: Session = Depends(get_db)):
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.thumbnail_path:
        # Generate default thumbnail at 0.5s
        thumb_path = os.path.join(THUMBS_DIR, f"thumb_{clip_id}.jpg")
        if os.path.exists(clip.clip_path):
            cmd = ["ffmpeg", "-y", "-i", clip.clip_path, "-ss", "0.5", "-vframes", "1", "-q:v", "2", thumb_path]
            subprocess.run(cmd, capture_output=True, timeout=30)
            clip.thumbnail_path = thumb_path
            db.commit()
        else:
            raise HTTPException(404, "No thumbnail available")
    
    if not os.path.exists(clip.thumbnail_path):
        raise HTTPException(404, "Thumbnail file not found")
    return FileResponse(clip.thumbnail_path, media_type="image/jpeg")

# ─── Style Learning ───────────────────────────────────────
@app.post("/api/style/save")
def api_save_style(name: str = Form(...), settings: str = Form("{}")):
    settings_dict = json.loads(settings)
    result = save_style(name, settings_dict)
    return result

@app.get("/api/style")
def api_list_styles():
    return load_all_styles()

@app.delete("/api/style/{name}")
def api_delete_style(name: str):
    ok = delete_style(name)
    return {"deleted": ok}

@app.post("/api/style/learn")
def api_learn_style(data: str = Form(...)):
    clip_data = json.loads(data)
    style = learn_from_example(clip_data)
    return style

# ─── Serve static assets (thumbnail images, clip downloads) ──
@app.get("/api/storage/{folder}/{filename}")
def get_storage_file(folder: str, filename: str):
    filepath = os.path.join(STORAGE_DIR, folder, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found")
    return FileResponse(filepath)
