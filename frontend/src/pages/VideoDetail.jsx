import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getVideo, processVideo, processDirect, autoClip, manualClip, clipDirect, splitClip, getClips, videoStreamUrl, clipStreamUrl } from '../api';

export default function VideoDetail() {
  const { id } = useParams();
  const [video, setVideo] = useState(null);
  const [clips, setClips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [clipping, setClipping] = useState(false);

  // Manual clip form
  const [manualStart, setManualStart] = useState('');
  const [manualEnd, setManualEnd] = useState('');

  // Split clip form
  const [splitLength, setSplitLength] = useState(30);
  const [splitOverlap, setSplitOverlap] = useState(0.5);

  const isDirect = video?.source === 'youtube_direct';

  const load = async () => {
    const data = await getVideo(id);
    setVideo(data);
    const c = await getClips(id);
    setClips(c);
    setLoading(false);
  };

  useEffect(() => { load(); }, [id]);

  const handleProcess = async () => {
    setProcessing(true);
    try {
      if (isDirect) {
        await processDirect(id);
      } else {
        await processVideo(id);
      }
      load();
    } catch (e) { alert('Error: ' + e.message); }
    setProcessing(false);
  };

  const handleAutoClip = async () => {
    setClipping(true);
    try {
      await autoClip(id);
      load();
    } catch (e) { alert('Error: ' + e.message); }
    setClipping(false);
  };

  const handleManualClip = async () => {
    const start = parseFloat(manualStart);
    const end = parseFloat(manualEnd);
    if (isNaN(start) || isNaN(end) || start >= end) {
      alert('Enter valid start and end times (start < end)');
      return;
    }
    setClipping(true);
    try {
      if (isDirect) {
        await clipDirect(id, start, end);
      } else {
        await manualClip(id, start, end);
      }
      load();
    } catch (e) { alert('Error: ' + e.message); }
    setClipping(false);
  };

  const handleSplitClip = async () => {
    setClipping(true);
    try {
      await splitClip(id, splitLength, splitOverlap);
      load();
    } catch (e) { alert('Error: ' + e.message); }
    setClipping(false);
  };

  const formatTime = (s) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  const extractVideoId = (url) => {
    if (!url) return null;
    const match = url.match(/(?:v=|\.be\/)([a-zA-Z0-9_-]{11})/);
    return match ? match[1] : null;
  };

  if (loading) return <p className="text-slate-400">Loading...</p>;
  if (!video) return <p className="text-red-400">Video not found</p>;

  const moments = video.moments?.moments || [];
  const ytVideoId = isDirect ? extractVideoId(video.source_url) : null;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left — Video Player */}
      <div className="lg:col-span-2">
        <div className="card mb-4">
          <h1 className="text-xl font-bold mb-1 truncate">{video.original_name}</h1>
          <p className="text-sm text-slate-400 mb-4">
            {isDirect ? '⚡ YouTube Direct' : video.source === 'youtube' ? '📺 YouTube' : '📁 Upload'}
            {' · '}{formatTime(video.duration)}
            {' · Status: '}<span className={video.status === 'ready' ? 'text-green-400' : 'text-yellow-400'}>{video.status}</span>
          </p>

          {isDirect ? (
            ytVideoId ? (
              <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
                <iframe
                  src={`https://www.youtube.com/embed/${ytVideoId}`}
                  className="absolute inset-0 w-full h-full rounded-lg"
                  allowFullScreen
                />
              </div>
            ) : (
              <div className="bg-slate-800 rounded-lg p-8 text-center text-slate-400">
                <p>📺 YouTube video preview</p>
                <a href={video.source_url} target="_blank" rel="noopener noreferrer" className="text-violet-400 text-sm mt-2 inline-block">
                  Open in YouTube →
                </a>
              </div>
            )
          ) : (
            <video src={videoStreamUrl(video.id)} controls className="w-full rounded-lg bg-black max-h-[500px]" />
          )}
        </div>

        {/* Actions */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">⚙️ Actions</h2>
          <div className="flex flex-wrap gap-2">
            {video.status !== 'ready' && (
              <button onClick={handleProcess} disabled={processing} className="btn">
                {processing ? 'Processing...' : isDirect ? '🔊 Transcribe Audio Only' : '🔊 Transcribe & Analyze'}
              </button>
            )}
            {video.status === 'ready' && (
              <button onClick={handleAutoClip} disabled={clipping} className="btn">
                {clipping ? 'Clipping...' : '🤖 Auto Clips'}
              </button>
            )}
          </div>
          {isDirect && (
            <p className="text-xs text-emerald-400 mt-2">⚡ Direct mode: only audio downloaded (~5MB)</p>
          )}
        </div>

        {/* Transcript */}
        {video.transcript && (
          <div className="card mb-4">
            <h2 className="font-semibold mb-3">📝 Transcript</h2>
            <div className="max-h-60 overflow-y-auto text-sm text-slate-300 space-y-1">
              {video.transcript.segments?.map((seg, i) => (
                <p key={i} className="hover:bg-slate-700/50 p-1 rounded">
                  <span className="text-violet-400 text-xs">{formatTime(seg.start)}</span>
                  {' '}{seg.text}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Detected Moments */}
        {moments.length > 0 && (
          <div className="card">
            <h2 className="font-semibold mb-3">🔥 Detected Moments</h2>
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {moments.map((m, i) => (
                <div key={i} className="bg-slate-800 border border-slate-700 rounded-lg p-3">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs text-violet-400 font-mono">
                      {formatTime(m.start)} → {formatTime(m.end)}
                    </span>
                    <span className="badge bg-violet-500/20 text-violet-300 text-xs">
                      Score: {m.score}
                    </span>
                  </div>
                  <p className="text-sm text-slate-200">{m.text}</p>
                  {m.types?.length > 0 && (
                    <div className="mt-1">
                      {m.types.map(t => <span key={t} className="tag">{t}</span>)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right — Clipping & Clips */}
      <div>
        {/* Manual Clip */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">✋ Manual Clip</h2>
          <div className="flex gap-2 mb-3">
            <input className="input" placeholder="Start (s)" value={manualStart} onChange={e => setManualStart(e.target.value)} />
            <input className="input" placeholder="End (s)" value={manualEnd} onChange={e => setManualEnd(e.target.value)} />
          </div>
          <button onClick={handleManualClip} disabled={clipping} className="btn w-full">
            {isDirect ? '⚡ Clip Direct from URL' : 'Create Manual Clip'}
          </button>
        </div>

        {/* Split Clip */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">🔀 Split into Reels</h2>
          <div className="mb-3">
            <label className="text-xs text-slate-400 mb-1 block">Target length (seconds)</label>
            <input type="range" min="15" max="60" value={splitLength} onChange={e => setSplitLength(Number(e.target.value))} className="w-full" />
            <span className="text-sm">{splitLength}s per clip</span>
          </div>
          <div className="mb-3">
            <label className="text-xs text-slate-400 mb-1 block">Overlap (seconds)</label>
            <input type="range" min="0" max="2" step="0.1" value={splitOverlap} onChange={e => setSplitOverlap(Number(e.target.value))} className="w-full" />
            <span className="text-sm">{splitOverlap}s overlap</span>
          </div>
          <button onClick={handleSplitClip} disabled={clipping} className="btn w-full">
            Split into Reels
          </button>
        </div>

        {/* Generated Clips */}
        <div className="card">
          <h2 className="font-semibold mb-3">🎬 Generated Clips ({clips.length})</h2>
          {clips.length === 0 && <p className="text-sm text-slate-500">No clips yet. Use one of the modes above.</p>}
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {clips.map(c => (
              <div key={c.id} className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
                <video src={clipStreamUrl(c.id)} className="w-full aspect-[9/16] bg-black object-cover" controls preload="metadata" />
                <div className="p-2">
                  <p className="text-xs text-slate-400 font-mono">{formatTime(c.start)} → {formatTime(c.end)}</p>
                  <div className="flex gap-1 mt-1">
                    <Link to={`/clip/${c.id}`} className="btn text-xs py-1 px-3 flex-1 text-center">Edit</Link>
                    <Link to={`/clip/${c.id}/thumbnail`} className="btn text-xs py-1 px-3 flex-1 text-center bg-emerald-600 hover:bg-emerald-500">Thumbnail</Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
