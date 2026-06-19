import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getVideo, processVideo, processDirect, processVideoBackground,
  autoClip, manualClip, clipDirect, splitClip,
  getClips, deleteClip, videoStreamUrl, clipStreamUrl,
  smartCropClip, analyzeViral
} from '../api';

function LoadingSpinner({ text = 'Loading...' }) {
  return (
    <div className="flex items-center justify-center py-10" role="status" aria-label={text}>
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">{text}</p>
      </div>
    </div>
  );
}

function formatTime(s) {
  if (s == null) return '0:00';
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function extractVideoId(url) {
  if (!url) return null;
  const match = url.match(/(?:v=|\\.be\/)([a-zA-Z0-9_-]{11})/);
  return match ? match[1] : null;
}

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

  // Smart crop
  const [smartStart, setSmartStart] = useState('');
  const [smartEnd, setSmartEnd] = useState('');
  const [smartQuality, setSmartQuality] = useState('balanced');

  // Viral analysis
  const [viralLoading, setViralLoading] = useState(false);
  const [viralClips, setViralClips] = useState([]);

  const abortRef = useRef(null);
  const pollRef = useRef(null);

  const isDirect = video?.source === 'youtube_direct';

  const load = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const [data, c] = await Promise.all([
        getVideo(id, { signal: controller.signal }),
        getClips(id, { signal: controller.signal })
      ]);
      if (!controller.signal.aborted) {
        setVideo(data);
        setClips(c.clips || c);
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        console.error('Failed to load video data:', e);
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
      }
    }
  }, [id]);

  useEffect(() => {
    load();
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, [load]);

  const handleProcess = useCallback(async () => {
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
  }, [id, isDirect, load]);

  const handleProcessBg = useCallback(async () => {
    setProcessing(true);
    try {
      await processVideoBackground(id);
      alert('Processing started in background. Check back in a few seconds.');
      // Poll for completion
      pollRef.current = setInterval(async () => {
        try {
          const v = await getVideo(id);
          if (v.status === 'ready' || v.status === 'error') {
            clearInterval(pollRef.current);
            pollRef.current = null;
            load();
          }
        } catch { /* ignore poll errors */ }
      }, 3000);
    } catch (e) { alert('Error: ' + e.message); }
    setProcessing(false);
  }, [id, load]);

  const handleAutoClip = useCallback(async () => {
    setClipping(true);
    try {
      await autoClip(id);
      load();
    } catch (e) { alert('Error: ' + e.message); }
    setClipping(false);
  }, [id, load]);

  const handleManualClip = useCallback(async () => {
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
  }, [id, isDirect, manualStart, manualEnd, load]);

  const handleSplitClip = useCallback(async () => {
    setClipping(true);
    try {
      await splitClip(id, splitLength, splitOverlap);
      load();
    } catch (e) { alert('Error: ' + e.message); }
    setClipping(false);
  }, [id, splitLength, splitOverlap, load]);

  // 🆕 Smart Crop
  const handleSmartCrop = useCallback(async () => {
    const start = parseFloat(smartStart);
    const end = parseFloat(smartEnd);
    if (isNaN(start) || isNaN(end) || start >= end) {
      alert('Enter valid start and end times');
      return;
    }
    setClipping(true);
    try {
      await smartCropClip(id, start, end, smartQuality);
      load();
    } catch (e) { alert('Smart crop failed: ' + e.message); }
    setClipping(false);
  }, [id, smartStart, smartEnd, smartQuality, load]);

  // 🆕 Viral Analysis
  const handleViralAnalysis = useCallback(async () => {
    setViralLoading(true);
    try {
      const result = await analyzeViral(id);
      setViralClips(result.clips || []);
      alert(`Found ${result.count} viral-worthy segments!`);
    } catch (e) { alert('Analysis failed: ' + e.message); }
    setViralLoading(false);
  }, [id]);

  const handleDeleteClip = useCallback(async (clipId) => {
    if (!confirm('Delete this clip?')) return;
    await deleteClip(clipId);
    load();
  }, [load]);

  if (loading) return <LoadingSpinner text="Loading video..." />;
  if (!video) return <p className="text-red-400" role="alert">Video not found</p>;

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
                  title="YouTube video player"
                  aria-label="YouTube video player"
                />
              </div>
            ) : (
              <div className="bg-slate-800 rounded-lg p-8 text-center text-slate-400">
                <p>📺 YouTube video preview</p>
                <a href={video.source_url} target="_blank" rel="noopener noreferrer" className="text-violet-400 text-sm mt-2 inline-block" aria-label="Open in YouTube">
                  Open in YouTube →
                </a>
              </div>
            )
          ) : (
            <video src={videoStreamUrl(video.id)} controls className="w-full rounded-lg bg-black max-h-[500px]" aria-label={`Video player for ${video.original_name}`} />
          )}
        </div>

        {/* Actions */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">⚙️ Actions</h2>
          <div className="flex flex-wrap gap-2">
            {video.status !== 'ready' && (
              <>
                <button onClick={handleProcess} disabled={processing} className="btn" aria-label="Transcribe and analyze video">
                  {processing ? 'Processing...' : isDirect ? '🔊 Transcribe (Sync)' : '🔊 Transcribe & Analyze'}
                </button>
                <button onClick={handleProcessBg} disabled={processing} className="btn bg-violet-600 hover:bg-violet-500" aria-label="Process in background">
                  {processing ? 'Starting...' : '⚡ Process in Background'}
                </button>
              </>
            )}
            {video.status === 'ready' && (
              <>
                <button onClick={handleAutoClip} disabled={clipping} className="btn" aria-label="Generate auto clips">
                  {clipping ? 'Clipping...' : '🤖 Auto Clips'}
                </button>
                <button onClick={handleViralAnalysis} disabled={viralLoading} className="btn bg-pink-600 hover:bg-pink-500" aria-label="Run AI viral analysis">
                  {viralLoading ? 'Analyzing...' : '🔥 AI Viral Analysis'}
                </button>
              </>
            )}
          </div>
          {isDirect && (
            <p className="text-xs text-emerald-400 mt-2">⚡ Direct mode: only audio downloaded (~5MB)</p>
          )}
        </div>

        {/* 🆕 Viral Analysis Results */}
        {viralClips.length > 0 && (
          <div className="card mb-4">
            <h2 className="font-semibold mb-3">🔥 AI Viral Analysis</h2>
            <div className="space-y-2">
              {viralClips.map((vc, i) => (
                <div key={i} className="bg-pink-500/10 border border-pink-500/30 rounded-lg p-3">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs text-pink-400 font-mono">
                      {formatTime(vc.start)} → {formatTime(vc.end)}
                    </span>
                    <span className="badge bg-pink-500/20 text-pink-300 text-xs">
                      Score: {vc.score}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-slate-200">{vc.title}</p>
                  <p className="text-xs text-slate-400 mt-1">{vc.description}</p>
                  <button
                    onClick={() => { setSmartStart(String(vc.start)); setSmartEnd(String(vc.end)); }}
                    className="text-xs text-violet-400 hover:text-violet-300 mt-1"
                    aria-label={`Use segment ${formatTime(vc.start)} to ${formatTime(vc.end)} in smart crop`}
                  >
                    → Use in Smart Crop
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Transcript */}
        {video.transcript && (
          <div className="card mb-4">
            <h2 className="font-semibold mb-3">📝 Transcript</h2>
            <div className="max-h-60 overflow-y-auto text-sm text-slate-300 space-y-1" role="list" aria-label="Video transcript segments">
              {video.transcript.segments?.map((seg, i) => (
                <p key={i} className="hover:bg-slate-700/50 p-1 rounded cursor-pointer"
                  onClick={() => { setManualStart(String(seg.start)); setManualEnd(String(seg.end)); }}
                  onKeyDown={e => { if (e.key === 'Enter') { setManualStart(String(seg.start)); setManualEnd(String(seg.end)); }}}
                  role="button"
                  tabIndex={0}
                  aria-label={`Transcript segment at ${formatTime(seg.start)}: ${seg.text}`}>
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
            <h2 className="font-semibold mb-3">🎯 Detected Moments</h2>
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
            <input className="input" placeholder="Start (s)" value={manualStart} onChange={e => setManualStart(e.target.value)} aria-label="Manual clip start time in seconds" />
            <input className="input" placeholder="End (s)" value={manualEnd} onChange={e => setManualEnd(e.target.value)} aria-label="Manual clip end time in seconds" />
          </div>
          <button onClick={handleManualClip} disabled={clipping} className="btn w-full" aria-label="Create manual clip">
            {isDirect ? '⚡ Clip Direct from URL' : 'Create Manual Clip'}
          </button>
        </div>

        {/* 🆕 Smart Crop (YOLOv8) */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">🎯 Smart Crop (YOLOv8)</h2>
          <p className="text-xs text-slate-400 mb-2">AI-powered content-aware cropping that tracks the subject</p>
          <div className="flex gap-2 mb-2">
            <input className="input" placeholder="Start (s)" value={smartStart} onChange={e => setSmartStart(e.target.value)} aria-label="Smart crop start time" />
            <input className="input" placeholder="End (s)" value={smartEnd} onChange={e => setSmartEnd(e.target.value)} aria-label="Smart crop end time" />
          </div>
          <select value={smartQuality} onChange={e => setSmartQuality(e.target.value)} className="input w-full mb-2" aria-label="Smart crop quality">
            <option value="draft">⚡ Draft (fast)</option>
            <option value="balanced">⚖️ Balanced</option>
            <option value="high">✨ High Quality</option>
          </select>
          <button onClick={handleSmartCrop} disabled={clipping} className="btn w-full bg-amber-600 hover:bg-amber-500" aria-label="Apply smart crop">
            {clipping ? 'Processing...' : '🎯 Smart Crop'}
          </button>
        </div>

        {/* Split Clip */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">🔀 Split into Reels</h2>
          <div className="mb-3">
            <label className="text-xs text-slate-400 mb-1 block" htmlFor="split-length">Target length (seconds)</label>
            <input id="split-length" type="range" min="15" max="60" value={splitLength} onChange={e => setSplitLength(Number(e.target.value))} className="w-full" aria-label="Split target length" />
            <span className="text-sm">{splitLength}s per clip</span>
          </div>
          <div className="mb-3">
            <label className="text-xs text-slate-400 mb-1 block" htmlFor="split-overlap">Overlap (seconds)</label>
            <input id="split-overlap" type="range" min="0" max="2" step="0.1" value={splitOverlap} onChange={e => setSplitOverlap(Number(e.target.value))} className="w-full" aria-label="Split overlap" />
            <span className="text-sm">{splitOverlap}s overlap</span>
          </div>
          <button onClick={handleSplitClip} disabled={clipping} className="btn w-full" aria-label="Split video into reels">
            Split into Reels
          </button>
        </div>

        {/* Generated Clips */}
        <div className="card">
          <h2 className="font-semibold mb-3">🎬 Generated Clips ({clips.length})</h2>
          {clips.length === 0 && <p className="text-sm text-slate-500">No clips yet. Use one of the modes above.</p>}
          <div className="space-y-3 max-h-[500px] overflow-y-auto" role="list" aria-label="Generated clips">
            {clips.map(c => (
              <div key={c.id} className="bg-slate-800 rounded-lg overflow-hidden border border-slate-700">
                <video src={clipStreamUrl(c.id)} className="w-full aspect-[9/16] bg-black object-cover" controls preload="metadata" aria-label={`Clip preview ${formatTime(c.start)} to ${formatTime(c.end)}`} />
                <div className="p-2">
                  <p className="text-xs text-slate-400 font-mono">
                    {formatTime(c.start)} → {formatTime(c.end)}
                    {c.mode && <span className="ml-2 badge bg-slate-600 text-xs">{c.mode}</span>}
                  </p>
                  <div className="flex gap-1 mt-1">
                    <Link to={`/clip/${c.id}`} className="btn text-xs py-1 px-3 flex-1 text-center" aria-label={`Edit clip ${c.id}`}>Edit</Link>
                    <Link to={`/clip/${c.id}/thumbnail`} className="btn text-xs py-1 px-3 flex-1 text-center bg-emerald-600 hover:bg-emerald-500" aria-label={`Create thumbnail for clip ${c.id}`}>🖼</Link>
                    <button onClick={() => handleDeleteClip(c.id)} className="btn text-xs py-1 px-3 bg-red-600 hover:bg-red-500" aria-label={`Delete clip ${c.id}`}>🗑</button>
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
