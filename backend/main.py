"""ClipCraft API — FastAPI backend"""
import os
import json
import uuid
import subprocess
import shutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from models.database import init_db, get_db, Video, Clip, StyleExample
from processing.transcriber import extract_audio, transcribe, get_video_duration, get_video_info, extract_audio_from_url, get_youtube_duration
from processing.analyzer import analyze_moments, get_hooks
from processing.clipper import create_vertical_clip, create_vertical_clip_from_url
from processing.opencode import create_clip_from_youtube, get_youtube_stream_url as opencode_get_stream
from processing.smart_crop import smart_crop_clip, get_video_info as smart_crop_info
from processing.viral_ai import analyze_viral_segments, analyze_with_gemini
from processing.subtitles import segments_to_srt, save_srt
from processing.style_learner import save_style, load_all_styles, delete_style, learn_from_example
from processing.translator import translate_srt, get_supported_languages
from processing.social_publish import publish_to_tiktok, publish_to_youtube, publish_to_instagram

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "storage")
VIDEOS_DIR = os.path.join(STORAGE_DIR, "videos")
CLIPS_DIR = os.path.join(STORAGE_DIR, "clips")
THUMBS_DIR = os.path.join(STORAGE_DIR, "thumbnails")
AUDIO_DIR = os.path.join(STORAGE_DIR, "audio")

for d in [STORAGE_DIR, VIDEOS_DIR, CLIPS_DIR, THUMBS_DIR, AUDIO_DIR]:
    os.makedirs(d, exist_ok=True)

MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB
ALLOWED_STORAGE_FOLDERS = {"videos", "clips", "thumbnails", "audio"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="ClipCraft API", version="1.0.0", lifespan=lifespan)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,https://frontend-hadijayyy.vercel.app,https://43-157-200-187.sslip.io").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large. Maximum 2GB.")
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    video_id = str(uuid.uuid4())[:8]
    filename = f"{video_id}{ext}"
    filepath = os.path.join(VIDEOS_DIR, filename)
    
    with open(filepath, "wb") as f:
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
COOKIES_DIR = os.path.join(STORAGE_DIR, "cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)

@app.post("/api/youtube")
async def import_youtube(url: str = Form(...), db: Session = Depends(get_db)):
    video_id = str(uuid.uuid4())[:8]
    filename = f"{video_id}.mp4"
    filepath = os.path.join(VIDEOS_DIR, filename)
    
    # Check for saved cookies
    cookie_args = []
    saved_cookies = os.path.join(COOKIES_DIR, "youtube_cookies.txt")
    if os.path.exists(saved_cookies):
        cookie_args = ["--cookies", saved_cookies]
    
    # Try multiple download strategies
    strategies = [
        # Strategy 1: Best quality up to 1080p (with cookies + EJS solver)
        ["yt-dlp", "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best", "-o", filepath, "--no-playlist", "--merge-output-format", "mp4", "--remote-components", "ejs:github"] + cookie_args + [url],
        # Strategy 2: Any format up to 1080p
        ["yt-dlp", "-f", "best[height<=1080]", "-o", filepath, "--no-playlist", "--remote-components", "ejs:github"] + cookie_args + [url],
        # Strategy 3: Any format at all
        ["yt-dlp", "-f", "best", "-o", filepath, "--no-playlist", "--remote-components", "ejs:github"] + cookie_args + [url],
    ]
    
    last_error = ""
    for cmd in strategies:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if os.path.exists(filepath) and os.path.getsize(filepath) > 10000:
            break
        last_error = result.stderr[-300:] if result.stderr else "unknown error"
    
    if not os.path.exists(filepath) or os.path.getsize(filepath) < 10000:
        if "Sign in to confirm" in last_error or "bot" in last_error.lower():
            raise HTTPException(403, "YouTube bot detection. Upload cookies.txt via POST /api/youtube/cookies first, then try again.")
        raise HTTPException(500, f"Failed to download YouTube video: {last_error}")
    
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

@app.post("/api/youtube/cookies")
async def upload_youtube_cookies(cookies: UploadFile = File(...)):
    """Upload YouTube cookies.txt to bypass bot detection.
    Export cookies from browser using extension like 'Get cookies.txt LOCALLY'."""
    content = await cookies.read()
    
    # Validate it looks like a cookies file
    text = content.decode("utf-8", errors="ignore")
    if not text.startswith("# Netscape") and "youtube.com" not in text:
        raise HTTPException(400, "Invalid cookies file. Use 'Get cookies.txt LOCALLY' browser extension to export YouTube cookies.")
    
    cookie_path = os.path.join(COOKIES_DIR, "youtube_cookies.txt")
    with open(cookie_path, "wb") as f:
        f.write(content)
    
    return {"status": "ok", "message": "YouTube cookies saved. Try importing again."}

@app.delete("/api/youtube/cookies")
async def delete_youtube_cookies():
    """Delete saved YouTube cookies."""
    cookie_path = os.path.join(COOKIES_DIR, "youtube_cookies.txt")
    if os.path.exists(cookie_path):
        os.remove(cookie_path)
    return {"status": "deleted"}

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
            raise RuntimeError("Failed to extract audio from URL")
        
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
    
    output = os.path.join(CLIPS_DIR, f"clip_{video_id}_direct_{str(uuid.uuid4())[:6]}.mp4")
    
    try:
        create_clip_from_youtube(video.source_url, output, start, end)
        
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
def list_videos(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str = Query(None, description="Search by filename"),
    source: str = Query(None, description="Filter by source"),
    status: str = Query(None, description="Filter by status")
):
    query = db.query(Video)
    
    if q:
        query = query.filter(Video.original_name.ilike(f"%{q}%"))
    if source:
        query = query.filter(Video.source == source)
    if status:
        query = query.filter(Video.status == status)
    
    total = query.count()
    videos = query.order_by(Video.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "videos": [
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
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.delete("/api/videos/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    # Delete video file
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete all clips
    clips = db.query(Clip).filter(Clip.video_id == video_id).all()
    for clip in clips:
        if clip.clip_path and os.path.exists(clip.clip_path):
            os.remove(clip.clip_path)
        if clip.thumbnail_path and os.path.exists(clip.thumbnail_path):
            os.remove(clip.thumbnail_path)
        db.delete(clip)
    
    # Delete audio files
    for ext in [".wav", "_transcript.json"]:
        audio_file = os.path.join(AUDIO_DIR, f"{video.id}{ext}")
        if os.path.exists(audio_file):
            os.remove(audio_file)
    
    db.delete(video)
    db.commit()
    return {"status": "deleted"}

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
    moments = sorted(data.get("moments", []), key=lambda x: x["score"], reverse=True)[:5]
    
    clips_data = []
    for i, m in enumerate(moments):
        output = os.path.join(CLIPS_DIR, f"clip_{video_id}_auto_{i}.mp4")
        try:
            create_vertical_clip(filepath, output, m["start"], m["end"])
            clip = Clip(
                video_id=video_id, clip_path=output,
                start_time=m["start"], end_time=m["end"],
                mode="auto"
            )
            clips_data.append((clip, m))
        except Exception:
            continue
    
    if clips_data:
        db.add_all([c for c, _ in clips_data])
        db.commit()
        for clip, _ in clips_data:
            db.refresh(clip)
    
    result = [
        {"id": clip.id, "start": m["start"], "end": m["end"],
         "path": clip.clip_path, "text": m["text"]}
        for clip, m in clips_data
    ]
    return {"clips": result, "count": len(result)}

@app.post("/api/clip/manual/{video_id}")
def manual_clip(video_id: int, start: float = Form(...), end: float = Form(...), db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    filepath = os.path.join(VIDEOS_DIR, video.filename)
    output = os.path.join(CLIPS_DIR, f"clip_{video_id}_manual_{str(uuid.uuid4())[:6]}.mp4")
    
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
def list_clips(
    video_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    query = db.query(Clip).filter(Clip.video_id == video_id)
    total = query.count()
    clips = query.order_by(Clip.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "clips": [
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
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

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
    if not clip:
        raise HTTPException(404, "Clip not found")
    if not clip.thumbnail_path or not os.path.exists(clip.thumbnail_path):
        # Generate default thumbnail at 0.5s
        thumb_path = os.path.join(THUMBS_DIR, f"thumb_{clip_id}.jpg")
        if clip.clip_path and os.path.exists(clip.clip_path):
            cmd = ["ffmpeg", "-y", "-i", clip.clip_path, "-ss", "0.5", "-vframes", "1", "-q:v", "2", thumb_path]
            subprocess.run(cmd, capture_output=True, timeout=30)
            clip.thumbnail_path = thumb_path
            db.commit()
        else:
            raise HTTPException(404, "No clip file available")
    
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
    if folder not in ALLOWED_STORAGE_FOLDERS:
        raise HTTPException(403, "Access denied")
    filepath = os.path.realpath(os.path.join(STORAGE_DIR, folder, filename))
    storage_real = os.path.realpath(STORAGE_DIR)
    if not filepath.startswith(storage_real + os.sep):
        raise HTTPException(403, "Access denied")
    if not os.path.exists(filepath):
        raise HTTPException(404, "File not found")
    return FileResponse(filepath)

# ─── Smart Crop (YOLOv8 content-aware) ─────────────────────
@app.post("/api/clip/smart/{video_id}")
def smart_clip(
    video_id: int,
    start: float = Form(...),
    end: float = Form(...),
    quality: str = Form("balanced"),
    db: Session = Depends(get_db)
):
    """Create a clip with YOLOv8 content-aware smart cropping."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")

    filepath = os.path.join(VIDEOS_DIR, video.filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Video file not found")

    output = os.path.join(CLIPS_DIR, f"clip_{video_id}_smart_{str(uuid.uuid4())[:6]}.mp4")

    try:
        smart_crop_clip(filepath, output, start, end, quality=quality)
        clip = Clip(
            video_id=video_id, clip_path=output,
            start_time=start, end_time=end,
            mode="smart"
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        return {"id": clip.id, "path": output, "start": start, "end": end, "mode": "smart"}
    except Exception as e:
        raise HTTPException(500, f"Smart crop failed: {str(e)}")

# ─── Viral AI Analysis ────────────────────────────────────
@app.post("/api/analyze/viral/{video_id}")
def analyze_viral(video_id: int, db: Session = Depends(get_db)):
    """Use AI to find the most viral-worthy segments from transcript."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    if not video.transcription:
        raise HTTPException(400, "No transcript available. Process video first.")

    transcript = json.loads(video.transcription)
    clips = analyze_viral_segments(transcript, video.source_url or "")

    # Store in moments_json
    video.moments_json = json.dumps({"viral_clips": clips})
    db.commit()

    return {"clips": clips, "count": len(clips)}

# ─── Multi-Format Export (9:16, 1:1, 16:9) ────────────────
ASPECT_RATIOS = {
    "9:16": {"width": 1080, "height": 1920, "label": "TikTok/Reels/Shorts"},
    "1:1": {"width": 1080, "height": 1080, "label": "Instagram Feed"},
    "16:9": {"width": 1920, "height": 1080, "label": "YouTube/Landscape"},
    "4:5": {"width": 1080, "height": 1350, "label": "Instagram Portrait"},
}

@app.get("/api/export/formats")
def list_export_formats():
    """List available export formats."""
    return {"formats": ASPECT_RATIOS}

@app.post("/api/clip/export/{clip_id}")
def export_clip(
    clip_id: int,
    format: str = Form("9:16"),
    db: Session = Depends(get_db)
):
    """Export a clip in a specific aspect ratio."""
    if format not in ASPECT_RATIOS:
        raise HTTPException(400, f"Invalid format. Available: {list(ASPECT_RATIOS.keys())}")
    
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    if not os.path.exists(clip.clip_path):
        raise HTTPException(404, "Clip file not found")
    
    ratio = ASPECT_RATIOS[format]
    safe_format = format.replace(":", "x")
    output = os.path.join(CLIPS_DIR, f"clip_{clip_id}_export_{safe_format}_{str(uuid.uuid4())[:6]}.mp4")
    
    # FFmpeg command for re-encoding to target aspect ratio
    w, h = ratio["width"], ratio["height"]
    cmd = [
        "ffmpeg", "-y",
        "-i", clip.clip_path,
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
               f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        output
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise HTTPException(500, f"Export failed: {result.stderr[-300:]}")
    
    return {"path": output, "format": format, "label": ratio["label"]}

# ─── Multi-Language Caption Translation ───────────────────
@app.get("/api/translate/languages")
def list_languages():
    """List supported translation languages."""
    return {"languages": get_supported_languages()}

@app.post("/api/clip/{clip_id}/translate")
def translate_clip_captions(
    clip_id: int,
    target_lang: str = Form("id"),
    db: Session = Depends(get_db)
):
    """Translate clip captions to target language."""
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
    
    # Translate
    translated = translate_srt(clip_segments, target_lang)
    
    return {"translated_srt": translated, "language": target_lang}

# ─── Direct Social Publishing ─────────────────────────────
@app.post("/api/publish/{clip_id}")
def publish_clip(
    clip_id: int,
    platform: str = Form(...),
    title: str = Form(""),
    description: str = Form(""),
    tags: str = Form(""),
    db: Session = Depends(get_db)
):
    """Publish a clip directly to social media platform."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(404, "Clip not found")
    if not os.path.exists(clip.clip_path):
        raise HTTPException(404, "Clip file not found")
    
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    
    try:
        if platform == "tiktok":
            result = publish_to_tiktok(clip.clip_path, title, description, tag_list)
        elif platform == "youtube":
            result = publish_to_youtube(clip.clip_path, title, description, tag_list)
        elif platform == "instagram":
            result = publish_to_instagram(clip.clip_path, title, description, tag_list)
        else:
            raise HTTPException(400, f"Unsupported platform: {platform}. Use: tiktok, youtube, instagram")
        
        return {"status": "published", "platform": platform, "result": result}
    except Exception as e:
        raise HTTPException(500, f"Publish failed: {str(e)}")

# ─── Background Processing ────────────────────────────────
@app.post("/api/process-bg/{video_id}")
def process_video_background(
    video_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process video in background (transcribe + analyze)."""
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(404, "Video not found")
    
    video.status = "processing"
    db.commit()
    
    background_tasks.add_task(_do_process_video, video_id)
    
    return {"status": "processing", "message": "Video processing started in background"}

def _do_process_video(video_id: int):
    """Background task: process video (transcribe + analyze)."""
    from models.database import SessionLocal
    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return
        
        filepath = os.path.join(VIDEOS_DIR, video.filename)
        if not os.path.exists(filepath):
            video.status = "error"
            db.commit()
            return
        
        audio_path = extract_audio(filepath, str(video.id))
        transcript = transcribe(audio_path, str(video.id))
        moments = analyze_moments(transcript)
        hooks = get_hooks(transcript)
        
        video.transcription = json.dumps(transcript)
        video.moments_json = json.dumps({"moments": moments, "hooks": hooks})
        video.status = "ready"
        db.commit()
    except Exception as e:
        video.status = "error"
        db.commit()
    finally:
        db.close()
