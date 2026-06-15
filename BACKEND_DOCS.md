# 🔧 ClipCraft Backend — Documentation

> FastAPI backend for video repurposing platform
> Version: 1.0.0 | Port: 8001

---

## 📁 Project Structure

```
backend/
├── main.py                    # FastAPI app + all endpoints
├── processing/
│   ├── clipper.py             # FFmpeg video clipping (9:16 vertical)
│   ├── transcriber.py         # Whisper transcription + audio extraction
│   ├── analyzer.py            # Rule-based viral moment detection
│   ├── smart_crop.py          # YOLOv8 content-aware cropping
│   ├── viral_ai.py            # AI viral segment analysis (LLM)
│   ├── translator.py          # Multi-language caption translation
│   ├── social_publish.py      # TikTok/YouTube/Instagram publishing
│   ├── subtitles.py           # SRT file generation
│   ├── style_learner.py       # Style learning (save/apply)
│   └── opencode.py            # YouTube URL resolver (yt-dlp fallback)
├── models/
│   └── database.py            # SQLAlchemy models + DB init
└── storage/                   # Runtime data (gitignored)
    ├── videos/                # Uploaded video files
    ├── clips/                 # Generated clip files
    ├── audio/                 # Extracted audio + transcripts
    └── thumbnails/            # Generated thumbnails
```

---

## 🚀 Setup

### Requirements

```bash
pip install fastapi uvicorn sqlalchemy python-multipart requests
pip install faster-whisper   # For transcription
pip install deep-translator   # For translation fallback
pip install ultralytics       # For YOLOv8 smart crop
pip install scenedetect[opencv]  # For scene detection
```

### System Dependencies

```bash
# FFmpeg (required)
apt install ffmpeg

# yt-dlp (for YouTube import)
pip install yt-dlp
```

### Run

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### Environment Variables

```bash
# AI (for viral analysis)
AI_BASE_URL=https://opencode.ai/zen/go/v1
AI_API_KEY=your_api_key
AI_MODEL=qwen3.5-plus

# Social Publishing (optional)
TIKTOK_ACCESS_TOKEN=
YOUTUBE_API_KEY=
YOUTUBE_ACCESS_TOKEN=
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_BUSINESS_ID=

# CORS
ALLOWED_ORIGINS=http://localhost:5173,https://your-domain.com
```

---

## 📡 API Endpoints

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |

---

### Video Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload video file (max 2GB) |
| `GET` | `/api/videos` | List videos (paginated) |
| `GET` | `/api/videos/{id}` | Get video details |
| `DELETE` | `/api/videos/{id}` | Delete video + all clips |
| `GET` | `/api/video/{id}/stream` | Stream video file |

**Query Parameters for `GET /api/videos`:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 50 | Results per page (1-200) |
| `offset` | int | 0 | Pagination offset |
| `q` | string | - | Search by filename |
| `source` | string | - | Filter: `upload`, `youtube`, `youtube_direct` |
| `status` | string | - | Filter: `uploaded`, `processing`, `ready`, `error` |

---

### YouTube Import

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/youtube` | Import YouTube video (full download) |
| `POST` | `/api/youtube-direct` | Import YouTube (audio only, ~5MB) |

---

### Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/process/{id}` | Transcribe + analyze (sync, blocks) |
| `POST` | `/api/process-bg/{id}` | Transcribe + analyze (background) |
| `POST` | `/api/process-direct/{id}` | Process YouTube direct video |

---

### Clipping

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/clip/auto/{id}` | Auto-clip from detected moments |
| `POST` | `/api/clip/manual/{id}` | Manual clip (start/end) |
| `POST` | `/api/clip/split/{id}` | Split into reels |
| `POST` | `/api/clip/smart/{id}` | Smart crop (YOLOv8) |
| `POST` | `/api/clip/direct/{id}` | Clip from YouTube URL |
| `POST` | `/api/clip/export/{id}` | Export in different aspect ratio |

**Export Formats:**

| Format | Resolution | Label |
|--------|------------|-------|
| `9:16` | 1080x1920 | TikTok/Reels/Shorts |
| `1:1` | 1080x1080 | Instagram Feed |
| `16:9` | 1920x1080 | YouTube/Landscape |
| `4:5` | 1080x1350 | Instagram Portrait |

---

### Clips

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/clips/{videoId}` | List clips for video |
| `GET` | `/api/clip/{id}` | Get clip details |
| `GET` | `/api/clip/{id}/stream` | Stream clip file |
| `GET` | `/api/clip/{id}/srt` | Get SRT subtitles |
| `POST` | `/api/clip/{id}/subtitles` | Save subtitles |
| `POST` | `/api/clip/{id}/overlays` | Save text overlays |
| `DELETE` | `/api/clip/{id}` | Delete clip |

---

### Thumbnail

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/thumbnail/{id}` | Generate thumbnail |
| `GET` | `/api/thumbnail/{id}/image` | Get thumbnail image |

---

### Translation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/translate/languages` | List supported languages |
| `POST` | `/api/clip/{id}/translate` | Translate clip captions |

**Supported Languages:**

| Code | Language |
|------|----------|
| `id` | Indonesian |
| `en` | English |
| `ms` | Malay |
| `th` | Thai |
| `vi` | Vietnamese |
| `tl` | Filipino |
| `ja` | Japanese |
| `ko` | Korean |
| `zh` | Chinese (Simplified) |
| `ar` | Arabic |
| `hi` | Hindi |
| `es` | Spanish |
| `pt` | Portuguese |
| `fr` | French |
| `de` | German |
| `ru` | Russian |
| `tr` | Turkish |
| `it` | Italian |
| `nl` | Dutch |
| `pl` | Polish |

---

### Social Publishing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/publish/{id}` | Publish to social platform |

**Publish Platforms:**

| Platform | Status |
|----------|--------|
| `tiktok` | Manual upload instructions (API token required for auto) |
| `youtube` | Manual upload instructions (API token required for auto) |
| `instagram` | Manual upload instructions (API token required for auto) |

---

### Style Learning

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/style` | List saved styles |
| `POST` | `/api/style/save` | Save style |
| `DELETE` | `/api/style/{name}` | Delete style |
| `POST` | `/api/style/learn` | Learn from example |

---

### Export Formats

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/export/formats` | List available export formats |

---

## 🗄️ Database Models

### Video

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `filename` | string | Stored filename |
| `original_name` | string | Original upload name |
| `source` | string | `upload`, `youtube`, `youtube_direct` |
| `source_url` | string | YouTube URL (if applicable) |
| `duration` | float | Duration in seconds |
| `status` | string | `uploaded`, `processing`, `ready`, `error` |
| `transcription` | text | JSON transcript from Whisper |
| `moments_json` | text | JSON detected moments |
| `created_at` | datetime | Creation timestamp |

### Clip

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Primary key |
| `video_id` | int | Foreign key to Video |
| `clip_path` | string | Path to clip file |
| `thumbnail_path` | string | Path to thumbnail |
| `start_time` | float | Start time in seconds |
| `end_time` | float | End time in seconds |
| `mode` | string | `auto`, `manual`, `split`, `smart`, `direct` |
| `subtitles_json` | text | Custom subtitles |
| `overlays_json` | text | Text overlay positions |
| `created_at` | datetime | Creation timestamp |

---

## 🔧 Key Functions

### clipper.py

```python
create_vertical_clip(input_path, output_path, start, end, width=720, height=1280)
create_vertical_clip_from_url(stream_url, output_path, start, end)
create_vertical_clip_from_youtube(youtube_url, output_path, start, end)
```

### transcriber.py

```python
extract_audio(video_path, audio_id) -> str
transcribe(audio_path, audio_id) -> dict
get_video_duration(video_path) -> float
get_video_info(video_path) -> dict
get_youtube_stream_url(url) -> str
```

### smart_crop.py

```python
smart_crop_video(input_path, output_path, start, end, width=720, height=1280, quality='balanced')
smart_crop_clip(input_path, output_path, start, end, width=720, height=1280, quality='balanced')
```

### viral_ai.py

```python
analyze_viral_segments(transcript, video_url='', top_n=5) -> list
```

### translator.py

```python
translate_srt(segments, target_lang) -> str
get_supported_languages() -> dict
```

### social_publish.py

```python
publish_to_tiktok(video_path, title, description, tags) -> dict
publish_to_youtube(video_path, title, description, tags) -> dict
publish_to_instagram(video_path, title, description, tags) -> dict
```

---

## ⚠️ Known Limitations

1. **YouTube Download** — VPS IP may be blocked by YouTube bot detection
2. **Social Publishing** — Requires API tokens (currently returns manual instructions)
3. **Translation** — Falls back to original text if AI API unavailable
4. **No Auth** — No user authentication (single-user mode)
5. **Local Storage** — Files stored on local disk (no S3/GCS)

---

## 📝 License

Internal use only.
