# 🎨 ClipCraft Frontend — Documentation

> React + Vite frontend for video repurposing platform
> Port: 3000 (dev) | Production: served via Caddy

---

## 📁 Project Structure

```
frontend/
├── src/
│   ├── App.jsx                 # Router + Layout
│   ├── main.jsx                # Entry point
│   ├── index.css               # Global styles (Tailwind)
│   ├── api.js                  # API client functions
│   └── pages/
│       ├── Dashboard.jsx       # Video library (list/search/paginate)
│       ├── Upload.jsx          # Upload video / YouTube import
│       ├── VideoDetail.jsx     # Video player + clipping tools
│       ├── ClipEditor.jsx      # Clip editor (overlays/subtitles/export/publish)
│       └── ThumbnailMaker.jsx  # Thumbnail generator
├── index.html
├── package.json
└── vite.config.js
```

---

## 🚀 Setup

### Requirements

- Node.js 18+
- npm or yarn

### Install

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
# Runs on http://localhost:5173
```

### Build for Production

```bash
npm run build
# Output: dist/
```

### Environment Variables

Create `.env`:

```bash
# Backend API URL
VITE_API_URL=http://localhost:8001
```

---

## 📄 Pages

### 1. Dashboard (`/`)

Video library with search and pagination.

**Features:**
- 🔍 Search videos by filename
- 📄 Pagination (12 per page)
- 🎬 Video hover preview
- 🗑 Delete videos
- Status badges (ready/processing/error)

**API Calls:**
```javascript
getVideos({ limit, offset, q, source, status })
deleteVideo(id)
videoStreamUrl(id)
```

---

### 2. Upload (`/upload`)

Import videos from file or YouTube.

**Features:**
- 📁 File upload (drag & drop)
- 📺 YouTube URL import (full download)
- ⚡ YouTube Direct (audio only, ~5MB)
- Progress bar during upload

**API Calls:**
```javascript
uploadVideo(file, onProgress)
importYoutube(url)
importYoutubeDirect(url)
```

---

### 3. VideoDetail (`/video/:id`)

Video player with clipping tools.

**Features:**
- 🎬 Video player (or YouTube embed for direct)
- 📝 Transcript display (click to select)
- 🎯 Detected moments with scores
- ⚙️ Actions:
  - 🔊 Transcribe & Analyze (sync)
  - ⚡ Process in Background
  - 🤖 Auto Clips (AI-detected)
  - 🔥 AI Viral Analysis
- ✂️ Clipping Tools:
  - ✋ Manual Clip (start/end)
  - 🎯 Smart Crop (YOLOv8)
  - 🔀 Split into Reels
- 🎬 Generated Clips list with edit/delete

**API Calls:**
```javascript
getVideo(id)
processVideo(id)
processVideoBackground(id)
autoClip(id)
manualClip(id, start, end)
splitClip(id, targetLength, overlap)
smartCropClip(videoId, start, end, quality)
analyzeViral(videoId)
getClips(id)
deleteClip(id)
```

---

### 4. ClipEditor (`/clip/:id`)

Edit clip with overlays, subtitles, export, and publish.

**Features:**
- 🎬 Video preview (9:16 aspect)
- ✏️ Text overlays (drag & drop)
- 💬 Subtitle editor (SRT format)
- 📐 Export format selector:
  - 9:16 (TikTok/Reels/Shorts)
  - 1:1 (Instagram Feed)
  - 16:9 (YouTube/Landscape)
  - 4:5 (Instagram Portrait)
- 🌐 Translate captions (20 languages)
- 📱 Publish to social media:
  - TikTok
  - YouTube
  - Instagram
- 🎨 Style learning (save/apply)
- 🖼 Thumbnail maker
- ⬇️ Download clip

**API Calls:**
```javascript
getClip(id)
clipStreamUrl(id)
getClipSrt(id)
saveSubtitles(id, json)
saveOverlays(id, json)
exportClip(clipId, format)
translateClip(clipId, targetLang)
publishClip(clipId, { platform, title, tags })
getStyles()
saveStyle(name, settings)
deleteStyle(name)
deleteClip(id)
```

---

### 5. ThumbnailMaker (`/clip/:id/thumbnail`)

Generate thumbnails from clip.

**Features:**
- 🎬 Video player with seek
- 📸 Capture frame at any timestamp
- ⬇️ Download thumbnail as JPEG

**API Calls:**
```javascript
clipStreamUrl(id)
generateThumbnail(clipId, timeSec)
thumbnailUrl(clipId)
```

---

## 🔧 API Client (`api.js`)

### Core Functions

```javascript
// Video management
getVideos({ limit, offset, q, source, status })
getVideo(id)
deleteVideo(id)
videoStreamUrl(id)

// Upload
uploadVideo(file, onProgress)
importYoutube(url)
importYoutubeDirect(url)

// Processing
processVideo(id)
processVideoBackground(id)
processDirect(id)

// Clipping
autoClip(id)
manualClip(id, start, end)
splitClip(id, targetLength, overlap)
clipDirect(id, start, end)

// Smart Crop
smartCropClip(videoId, start, end, quality)

// Viral Analysis
analyzeViral(videoId)

// Clips
getClips(videoId)
getClip(id)
clipStreamUrl(id)
deleteClip(id)

// Subtitles
getClipSrt(id)
saveSubtitles(id, json)
saveOverlays(id, json)

// Thumbnail
generateThumbnail(clipId, timeSec)
thumbnailUrl(clipId)

// Export
getExportFormats()
exportClip(clipId, format)

// Translation
getSupportedLanguages()
translateClip(clipId, targetLang)

// Publishing
publishClip(clipId, { platform, title, description, tags })

// Styles
getStyles()
saveStyle(name, settings)
deleteStyle(name)
```

---

## 🎨 Styling

Uses **Tailwind CSS** with dark theme.

### Color Palette

| Element | Color |
|---------|-------|
| Primary | Violet (`violet-500`) |
| Success | Green (`green-500`) |
| Warning | Yellow (`yellow-500`) |
| Error | Red (`red-500`) |
| Background | Slate (`slate-900`) |
| Cards | Slate (`slate-800`) |

### Components

- `.btn` — Button base style
- `.card` — Card container
- `.input` — Input field
- `.badge` — Status badge
- `.tag` — Small tag label

---

## 📱 Responsive Design

| Breakpoint | Layout |
|------------|--------|
| Mobile (< 640px) | Single column |
| Tablet (640-1024px) | 2 columns |
| Desktop (> 1024px) | 3 columns |

---

## 🔄 State Management

Uses React `useState` + `useEffect` (no Redux/Zustand).

### State Flow

```
Dashboard → getVideos() → setVideos()
    ↓
VideoDetail → getVideo(id) → setVideo()
           → getClips(id) → setClips()
    ↓
ClipEditor → getClip(id) → setClip()
           → getClipSrt(id) → setSrtData()
           → getStyles() → setStyles()
```

---

## ⚠️ Known Limitations

1. **No Auth** — Single-user mode, no login
2. **No Real-time Updates** — Must refresh to see background job status
3. **No Offline Support** — Requires backend connection
4. **Large Files** — Upload limited to 2GB (backend constraint)
5. **YouTube Embed** — Only works for `youtube_direct` source videos

---

## 📝 License

Internal use only.
