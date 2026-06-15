# 🎬 ClipCraft

Turn long videos into short vertical clips for **TikTok**, **YouTube Shorts**, and **Instagram Reels**.

Upload a video or paste a YouTube link → get smart AI-detected clips with vertical 9:16 format, blurred backgrounds, and auto-subtitles.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **📁 Upload Any Video** | MP4, MOV, AVI, MKV — drag & drop or click to upload |
| **📺 YouTube Import** | Paste any YouTube URL, auto-download & process |
| **🔊 Auto Transcription** | Local Whisper AI — no API key, no cost |
| **🧠 Smart Moment Detection** | Hooks, emotional peaks, surprise moments, questions |
| **🤖 Auto Clips** | AI picks the best moments, creates vertical clips |
| **✋ Manual Clips** | Enter exact start/end timestamps |
| **🔀 Split Mode** | Split entire video into back-to-back reels |
| **📐 Vertical 9:16** | Smart crop + blurred background for any source format |
| **💬 Subtitle Editor** | Edit auto-generated SRT subtitles per clip |
| **✏️ Text Overlays** | Drag text anywhere on the video preview |
| **🖼 Thumbnail Maker** | Capture any frame as a thumbnail |
| **🎨 Style Learning** | Save & reuse your clipping style preferences |
| **📂 Video Library** | Reusable library — no re-uploading same files |

---

## 🚀 Tech Stack

- **Frontend:** React + Vite + TailwindCSS
- **Backend:** Python FastAPI + SQLite
- **AI:** faster-whisper (local transcription)
- **Video:** FFmpeg (clipping, vertical crop, blur background)
- **YouTube:** yt-dlp
- **Deployment:** Vercel (frontend) + VPS (backend)

---

## 📦 Setup (Self-Hosted)

### Prerequisites

- Python 3.10+
- Node.js 18+
- FFmpeg (`apt install ffmpeg`)

### Backend

```bash
# Clone
git clone https://github.com/hadijayyy/clipcraft.git
cd clipcraft/backend

# Install deps
pip install fastapi uvicorn sqlalchemy python-multipart faster-whisper yt-dlp

# Run
uvicorn main:app --host 0.0.0.0 --port 8001
```

Backend runs at `http://localhost:8001`

### Frontend

```bash
cd clipcraft/frontend

# Install
npm install

# Set API URL
echo "VITE_API_URL=http://localhost:8001" > .env

# Dev
npm run dev

# Build for production
npm run build
```

---

## 🎯 How It Works

```
Upload / YouTube URL
        ↓
  Extract Audio (FFmpeg)
        ↓
  Transcribe (Whisper AI)
        ↓
  Analyze for Moments
  • Hooks (short punchy lines)
  • Questions (?)
  • Emotional peaks
  • Surprise/statistics
  • Imperative commands
        ↓
  Create Vertical Clips (FFmpeg)
  • 9:16 crop or pad with blur
  • Include audio + subtitles
        ↓
  Edit & Download
  • Text overlays
  • Subtitle editor
  • Thumbnail capture
```

---

## 📖 Usage

1. **Upload** — Click Upload, select file or paste YouTube URL
2. **Wait** — Backend transcribes audio and detects interesting moments
3. **Choose Mode:**
   - 🤖 **Auto** — AI picks top moments based on score
   - ✋ **Manual** — Enter start/end timestamps yourself
   - 🔀 **Split** — Divide entire video into equal chunks (adjustable length + overlap)
4. **Edit** — Click Edit on any clip to add subtitles and text overlays
5. **Thumbnail** — Click Thumbnail to capture the perfect frame
6. **Download** — Get your MP4 clip, ready for TikTok/Shorts/Reels

---

## 🎨 Style Learning

Train ClipCraft on your content style:

1. Edit a clip the way you like (text placement, font size, colors)
2. Go to **Style Learning** panel in the editor
3. Enter a name and click **Save**
4. Apply saved styles to future clips

---

## ⚙️ Configuration

### Backend Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 8001 | Backend server port |
| `STORAGE_DIR` | `./storage` | Video/clip storage location |

### Frontend Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8001` | Backend API URL |

---

## 📁 Project Structure

```
clipcraft/
├── backend/
│   ├── main.py                    # FastAPI routes
│   ├── models/
│   │   └── database.py            # SQLite ORM
│   ├── processing/
│   │   ├── transcriber.py         # Whisper transcription
│   │   ├── analyzer.py            # Moment detection
│   │   ├── clipper.py             # FFmpeg clipping
│   │   ├── subtitles.py           # SRT generation
│   │   └── style_learner.py       # Style profiles
│   └── storage/                   # Videos, clips, thumbnails
│
├── frontend/
│   ├── src/
│   │   ├── api.js                 # API client
│   │   ├── App.jsx                # Router + navigation
│   │   └── pages/
│   │       ├── Dashboard.jsx      # Video library
│   │       ├── Upload.jsx         # Upload / YouTube import
│   │       ├── VideoDetail.jsx    # Player, transcript, moments, clips
│   │       ├── ClipEditor.jsx     # Text overlays + subtitles
│   │       └── ThumbnailMaker.jsx # Frame capture
│   └── vite.config.js
│
└── README.md
```

---

## 🐛 Troubleshooting

| Issue | Fix |
|-------|-----|
| "Transcription failed" | Check FFmpeg is installed: `ffmpeg -version` |
| "Video file not found" | Ensure `backend/storage/videos/` exists and has write permissions |
| Blank frontend page | Check `VITE_API_URL` in `.env` or Vercel env vars |
| Slow first transcription | Whisper downloads model (~150MB) on first run |
| YouTube import fails | Update yt-dlp: `pip install -U yt-dlp` |

---

## 📄 License

MIT

---

Built with ❤️ for content creators
