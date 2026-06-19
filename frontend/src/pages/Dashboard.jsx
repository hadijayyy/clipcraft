import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { getVideos, deleteVideo, videoStreamUrl } from '../api';

function formatDuration(s) {
  if (!s) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function VideoCard({ video, onDelete }) {
  return (
    <div className="card hover:border-violet-500/50 transition overflow-hidden">
      <div className="relative aspect-video bg-slate-800 rounded-lg mb-3 overflow-hidden">
        <video
          src={videoStreamUrl(video.id)}
          className="w-full h-full object-cover"
          preload="metadata"
          onMouseOver={e => e.currentTarget.play()}
          onMouseOut={e => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
          muted
          loop
          playsInline
          aria-label={`Preview of ${video.original_name}`}
        />
        <span className="absolute bottom-2 right-2 bg-black/70 text-xs px-2 py-1 rounded">
          {formatDuration(video.duration)}
        </span>
        <span className={`absolute top-2 left-2 badge text-xs ${video.status === 'ready' ? 'bg-green-500/20 text-green-400' : video.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' : video.status === 'error' ? 'bg-red-500/20 text-red-400' : 'bg-slate-500/20 text-slate-400'}`}>
          {video.status}
        </span>
      </div>

      <h3 className="font-semibold truncate mb-1">{video.original_name}</h3>
      <p className="text-xs text-slate-400 mb-3">
        {video.source === 'youtube' ? '📺 YouTube' : '📁 Upload'}
        {video.has_transcript && ' · transcribed'}
      </p>

      <div className="flex gap-2">
        <Link to={`/video/${video.id}`} className="btn flex-1 text-center text-sm" aria-label={`Open ${video.original_name}`}>
          Open
        </Link>
        <button
          onClick={() => onDelete(video.id)}
          className="px-3 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-sm"
          aria-label={`Delete ${video.original_name}`}
        >
          🗑
        </button>
      </div>
    </div>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-10" role="status" aria-label="Loading videos">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">Loading videos...</p>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const LIMIT = 12;

  const abortRef = useRef(null);

  const load = useCallback(async (query = '', offset = 0) => {
    // Cancel previous request
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    try {
      const data = await getVideos({ limit: LIMIT, offset, q: query || undefined, signal: controller.signal });
      if (!controller.signal.aborted) {
        setVideos(data.videos || []);
        setTotal(data.total || 0);
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        console.error('Failed to load videos:', e);
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    load();
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [load]);

  const handleSearch = useCallback((e) => {
    e.preventDefault();
    setPage(0);
    load(search, 0);
  }, [search, load]);

  const handleClearSearch = useCallback(() => {
    setSearch('');
    setPage(0);
    load('', 0);
  }, [load]);

  const handleDelete = useCallback(async (id) => {
    if (!confirm('Delete this video?')) return;
    try {
      await deleteVideo(id);
      load(search, page);
    } catch (e) {
      console.error('Delete failed:', e);
    }
  }, [search, page, load]);

  const handlePrevPage = useCallback(() => {
    const p = page - 1;
    setPage(p);
    load(search, p * LIMIT);
  }, [page, search, load]);

  const handleNextPage = useCallback(() => {
    const p = page + 1;
    setPage(p);
    load(search, p * LIMIT);
  }, [page, search, load]);

  const totalPages = Math.ceil(total / LIMIT);

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">🎬 Video Library</h1>
        <Link to="/upload" className="btn" aria-label="Upload a new video">+ Upload</Link>
      </div>

      {/* Search + Filter */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6" role="search" aria-label="Search videos">
        <input
          type="text"
          placeholder="Search videos..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:border-violet-500 outline-none"
          aria-label="Search query"
        />
        <button type="submit" className="btn" aria-label="Search">🔍 Search</button>
        {search && (
          <button type="button" onClick={handleClearSearch} className="btn bg-slate-700" aria-label="Clear search">
            ✕ Clear
          </button>
        )}
      </form>

      {loading && <LoadingSpinner />}

      {!loading && videos.length === 0 && (
        <div className="card text-center py-16" role="status">
          <p className="text-5xl mb-4">🎬</p>
          <p className="text-xl text-slate-300 mb-2">{search ? 'No results found' : 'No videos yet'}</p>
          <p className="text-slate-400 mb-6">
            {search ? 'Try a different search term' : 'Upload a video or paste a YouTube link to get started'}
          </p>
          {!search && <Link to="/upload" className="btn text-lg px-8 py-3">Upload Your First Video</Link>}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" role="list" aria-label="Video list">
        {videos.map(v => (
          <div key={v.id} role="listitem">
            <VideoCard video={v} onDelete={handleDelete} />
          </div>
        ))}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="flex justify-center items-center gap-4 mt-6" aria-label="Pagination">
          <button
            onClick={handlePrevPage}
            disabled={page === 0}
            className="btn disabled:opacity-30"
            aria-label="Previous page"
          >
            ← Prev
          </button>
          <span className="text-slate-400 text-sm" aria-current="page">
            Page {page + 1} of {totalPages} ({total} videos)
          </span>
          <button
            onClick={handleNextPage}
            disabled={page >= totalPages - 1}
            className="btn disabled:opacity-30"
            aria-label="Next page"
          >
            Next →
          </button>
        </nav>
      )}
    </div>
  );
}
