import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getVideos, deleteVideo, videoStreamUrl } from '../api';

export default function Dashboard() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const data = await getVideos();
      setVideos(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const handleDelete = async (id) => {
    if (!confirm('Hapus video ini?')) return;
    await deleteVideo(id);
    load();
  };

  const fmtDur = (s) => {
    if (!s) return '0:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Video Library</h1>
        <Link to="/upload" className="btn">+ Upload</Link>
      </div>

      {loading && <p className="text-slate-400">Loading...</p>}

      {!loading && videos.length === 0 && (
        <div className="card text-center py-16">
          <p className="text-5xl mb-4">🎬</p>
          <p className="text-xl text-slate-300 mb-2">No videos yet</p>
          <p className="text-slate-400 mb-6">Upload a video or paste a YouTube link to get started</p>
          <Link to="/upload" className="btn text-lg px-8 py-3">Upload Your First Video</Link>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {videos.map(v => (
          <div key={v.id} className="card hover:border-violet-500/50 transition overflow-hidden">
            <div className="relative aspect-video bg-slate-800 rounded-lg mb-3 overflow-hidden">
              <video
                src={videoStreamUrl(v.id)}
                className="w-full h-full object-cover"
                preload="metadata"
                onMouseOver={e => e.currentTarget.play()}
                onMouseOut={e => { e.currentTarget.pause(); e.currentTarget.currentTime = 0; }}
                muted
                loop
                playsInline
              />
              <span className="absolute bottom-2 right-2 bg-black/70 text-xs px-2 py-1 rounded">
                {fmtDur(v.duration)}
              </span>
              <span className={`absolute top-2 left-2 badge text-xs ${v.status === 'ready' ? 'bg-green-500/20 text-green-400' : v.status === 'processing' ? 'bg-yellow-500/20 text-yellow-400' : v.status === 'error' ? 'bg-red-500/20 text-red-400' : 'bg-slate-500/20 text-slate-400'}`}>
                {v.status}
              </span>
            </div>

            <h3 className="font-semibold truncate mb-1">{v.original_name}</h3>
            <p className="text-xs text-slate-400 mb-3">
              {v.source === 'youtube' ? '📺 YouTube' : '📁 Upload'}
              {v.has_transcript && ' · transcribed'}
            </p>

            <div className="flex gap-2">
              <Link to={`/video/${v.id}`} className="btn flex-1 text-center text-sm">Open</Link>
              <button onClick={() => handleDelete(v.id)} className="px-3 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-sm">🗑</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
