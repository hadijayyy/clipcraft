import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getClip, clipStreamUrl, getClipSrt, saveSubtitles, saveOverlays,
  getStyles, saveStyle, deleteStyle, deleteClip,
  exportClip, getExportFormats, translateClip, getSupportedLanguages, publishClip
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

export default function ClipEditor() {
  const { id } = useParams();
  const [clip, setClip] = useState(null);
  const [srtData, setSrtData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Text overlays
  const [overlays, setOverlays] = useState([]);
  const [dragIdx, setDragIdx] = useState(null);
  const [newText, setNewText] = useState('');

  // Subtitle editing
  const [subtitleText, setSubtitleText] = useState('');
  const [styles, setStyles] = useState({});
  const [styleName, setStyleName] = useState('');

  // Export
  const [exportFormats, setExportFormats] = useState({});
  const [exportFormat, setExportFormat] = useState('9:16');
  const [exporting, setExporting] = useState(false);

  // Translate
  const [languages, setLanguages] = useState({});
  const [targetLang, setTargetLang] = useState('id');
  const [translating, setTranslating] = useState(false);
  const [translatedSrt, setTranslatedSrt] = useState('');

  // Publish
  const [publishing, setPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState(null);

  const videoRef = useRef(null);
  const containerRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;

    const load = async () => {
      try {
        const [c, formats, langs] = await Promise.all([
          getClip(id, { signal: controller.signal }),
          getExportFormats({ signal: controller.signal }),
          getSupportedLanguages({ signal: controller.signal })
        ]);
        if (controller.signal.aborted) return;
        setClip(c);
        setExportFormats(formats.formats || {});
        setLanguages(langs.languages || {});
        if (c.overlays) {
          try { setOverlays(JSON.parse(c.overlays)); } catch {}
        }
        const srt = await getClipSrt(id, { signal: controller.signal });
        if (controller.signal.aborted) return;
        setSrtData(srt);
        if (srt?.srt) setSubtitleText(srt.srt);
        const st = await getStyles({ signal: controller.signal });
        if (controller.signal.aborted) return;
        setStyles(st || {});
      } catch (e) {
        if (e.name !== 'AbortError') {
          console.error('Failed to load clip:', e);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    };
    load();

    return () => {
      controller.abort();
    };
  }, [id]);

  const handleSaveOverlays = useCallback(async () => {
    await saveOverlays(id, JSON.stringify(overlays));
    alert('Overlays saved!');
  }, [id, overlays]);

  const handleSaveSubtitles = useCallback(async () => {
    await saveSubtitles(id, subtitleText);
    alert('Subtitles saved!');
  }, [id, subtitleText]);

  const addOverlay = useCallback(() => {
    if (!newText.trim()) return;
    setOverlays(prev => [...prev, {
      id: Date.now(),
      text: newText,
      x: 50, y: 50,
      fontSize: 24,
      color: '#ffffff',
      bgColor: 'rgba(0,0,0,0.5)',
    }]);
    setNewText('');
  }, [newText]);

  const removeOverlay = useCallback((idx) => {
    setOverlays(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const handleMouseDown = useCallback((idx) => setDragIdx(idx), []);

  const handleMouseMove = useCallback((e) => {
    if (dragIdx === null || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setOverlays(prev => {
      const next = [...prev];
      next[dragIdx] = { ...next[dragIdx], x: Math.max(0, Math.min(100, x)), y: Math.max(0, Math.min(100, y)) };
      return next;
    });
  }, [dragIdx]);

  const handleMouseUp = useCallback(() => setDragIdx(null), []);

  const handleKeyMove = useCallback((idx, dx, dy) => {
    setOverlays(prev => {
      const next = [...prev];
      next[idx] = {
        ...next[idx],
        x: Math.max(0, Math.min(100, (next[idx].x || 0) + dx)),
        y: Math.max(0, Math.min(100, (next[idx].y || 0) + dy)),
      };
      return next;
    });
  }, []);

  const handleSaveStyle = useCallback(async () => {
    if (!styleName.trim()) return;
    const savedSettings = {
      overlayCount: overlays.length,
      fontSizes: overlays.map(o => o.fontSize),
      colors: overlays.map(o => o.color),
      bgColors: overlays.map(o => o.bgColor),
    };
    try {
      await saveStyle(styleName, savedSettings);
      setStyles(prev => ({
        ...prev,
        [styleName]: { name: styleName, settings: savedSettings }
      }));
      alert(`Style "${styleName}" saved!`);
      setStyleName('');
    } catch (e) {
      alert('Failed to save style: ' + e.message);
    }
  }, [styleName, overlays]);

  const applyStyle = useCallback((name) => {
    const style = styles[name];
    if (!style?.settings) return;
    const { fontSizes = [], colors = [] } = style.settings;
    setOverlays(prev =>
      prev.map((ov, i) => ({
        ...ov,
        fontSize: fontSizes[i] ?? ov.fontSize,
        color: colors[i] ?? ov.color,
      }))
    );
  }, [styles]);

  // ─── Export ────────────────────────────────────────────
  const handleExport = useCallback(async () => {
    setExporting(true);
    try {
      const result = await exportClip(id, exportFormat);
      alert(`Exported to ${exportFormat} (${exportFormats[exportFormat]?.label})`);
      // Offer download
      const link = document.createElement('a');
      link.href = `/api/storage/clips/${result.path.split('/').pop()}`;
      link.download = `clip_${id}_${exportFormat.replace(':', 'x')}.mp4`;
      link.click();
    } catch (e) {
      alert('Export failed: ' + e.message);
    }
    setExporting(false);
  }, [id, exportFormat, exportFormats]);

  // ─── Translate ─────────────────────────────────────────
  const handleTranslate = useCallback(async () => {
    setTranslating(true);
    try {
      const result = await translateClip(id, targetLang);
      setTranslatedSrt(result.translated_srt || '(no speech detected)');
      alert(`Translated to ${languages[targetLang] || targetLang}`);
    } catch (e) {
      alert('Translation failed: ' + e.message);
    }
    setTranslating(false);
  }, [id, targetLang, languages]);

  // ─── Publish ───────────────────────────────────────────
  const handlePublish = useCallback(async (platform) => {
    setPublishing(true);
    setPublishResult(null);
    try {
      const result = await publishClip(id, {
        platform,
        title: `Clip ${id}`,
        tags: 'viral,shorts'
      });
      setPublishResult(result);
    } catch (e) {
      alert('Publish failed: ' + e.message);
    }
    setPublishing(false);
  }, [id]);

  const handleDeleteClip = useCallback(async () => {
    if (!confirm('Delete this clip permanently?')) return;
    await deleteClip(id);
    window.location.href = '/';
  }, [id]);

  const handleNewTextKeyDown = useCallback((e) => {
    if (e.key === 'Enter') addOverlay();
  }, [addOverlay]);

  const handleStyleNameKeyDown = useCallback((e) => {
    if (e.key === 'Enter') handleSaveStyle();
  }, [handleSaveStyle]);

  if (loading) return <LoadingSpinner text="Loading editor..." />;
  if (!clip) return <p className="text-red-400" role="alert">Clip not found</p>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Video Preview */}
      <div className="lg:col-span-2">
        <div className="card mb-4">
          <div className="flex justify-between items-start mb-3">
            <h1 className="text-xl font-bold">Clip Editor</h1>
            <div className="flex gap-2">
              <Link to={`/clip/${id}/thumbnail`} className="btn text-sm bg-emerald-600 hover:bg-emerald-500" aria-label="Create thumbnail">
                🖼 Thumbnail
              </Link>
              <button onClick={handleDeleteClip} className="btn text-sm bg-red-600 hover:bg-red-500" aria-label="Delete clip">
                🗑 Delete
              </button>
            </div>
          </div>

          <div ref={containerRef} className="relative bg-black rounded-lg overflow-hidden" style={{ maxWidth: '400px', margin: '0 auto' }}>
            <video ref={videoRef} src={clipStreamUrl(id)} controls className="w-full aspect-[9/16]" aria-label="Clip video player" />

            {/* Draggable Text Overlays */}
            {overlays.map((ov, i) => (
              <div
                key={ov.id}
                onMouseDown={() => handleMouseDown(i)}
                onKeyDown={e => {
                  const STEP = 2;
                  switch (e.key) {
                    case 'ArrowLeft': handleKeyMove(i, -STEP, 0); e.preventDefault(); break;
                    case 'ArrowRight': handleKeyMove(i, STEP, 0); e.preventDefault(); break;
                    case 'ArrowUp': handleKeyMove(i, 0, -STEP); e.preventDefault(); break;
                    case 'ArrowDown': handleKeyMove(i, 0, STEP); e.preventDefault(); break;
                  }
                }}
                role="button"
                tabIndex={0}
                aria-label={`Overlay text: ${ov.text}. Use arrow keys to reposition.`}
                style={{
                  position: 'absolute',
                  left: `${ov.x}%`, top: `${ov.y}%`,
                  transform: 'translate(-50%, -50%)',
                  fontSize: `${ov.fontSize}px`, color: ov.color,
                  backgroundColor: ov.bgColor,
                  padding: '4px 12px', borderRadius: '6px',
                  cursor: dragIdx === i ? 'grabbing' : 'grab',
                  userSelect: 'none', whiteSpace: 'nowrap', zIndex: 10,
                }}
              >
                {ov.text}
                <button onClick={() => removeOverlay(i)}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center"
                  style={{ zIndex: 11 }}
                  aria-label={`Remove overlay: ${ov.text}`}>×</button>
              </div>
            ))}
          </div>

          {/* Add Overlay */}
          <div className="mt-4 flex gap-2">
            <input className="input flex-1" placeholder="Text to show on video..." value={newText}
              onChange={e => setNewText(e.target.value)}
              onKeyDown={handleNewTextKeyDown}
              aria-label="New overlay text" />
            <button onClick={addOverlay} className="btn" aria-label="Add text overlay">Add Text</button>
          </div>

          {/* Overlay Controls */}
          {overlays.length > 0 && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {overlays.map((ov, i) => (
                <div key={ov.id} className="bg-slate-800 p-2 rounded text-xs">
                  <p className="truncate text-slate-300 mb-1">{ov.text}</p>
                  <label className="text-xs text-slate-500">Font size</label>
                  <input type="range" min="12" max="72" value={ov.fontSize}
                    onChange={e => { const n = [...overlays]; n[i] = { ...n[i], fontSize: Number(e.target.value) }; setOverlays(n); }}
                    className="w-full"
                    aria-label={`Font size for overlay ${i + 1}`} />
                  <label className="text-xs text-slate-500">Color</label>
                  <input type="color" value={ov.color}
                    onChange={e => { const n = [...overlays]; n[i] = { ...n[i], color: e.target.value }; setOverlays(n); }}
                    className="w-full h-6 rounded mt-1"
                    aria-label={`Color for overlay ${i + 1}`} />
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2 mt-3">
            <button onClick={handleSaveOverlays} className="btn flex-1" aria-label="Save overlays">💾 Save Overlays</button>
          </div>
        </div>
      </div>

      {/* Right Sidebar */}
      <div>
        {/* Subtitles */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">💬 Subtitles</h2>
          <textarea className="input font-mono text-xs h-40" value={subtitleText}
            onChange={e => setSubtitleText(e.target.value)}
            aria-label="Subtitle text editor" />
          <button onClick={handleSaveSubtitles} className="btn w-full mt-2" aria-label="Save subtitles">💾 Save Subtitles</button>
        </div>

        {/* 🆕 Export Format */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">📐 Export Format</h2>
          <select value={exportFormat} onChange={e => setExportFormat(e.target.value)}
            className="input w-full mb-2" aria-label="Export format">
            {Object.entries(exportFormats).map(([key, fmt]) => (
              <option key={key} value={key}>{key} — {fmt.label}</option>
            ))}
          </select>
          <button onClick={handleExport} disabled={exporting} className="btn w-full" aria-label="Export clip">
            {exporting ? '⏳ Exporting...' : `📤 Export ${exportFormat}`}
          </button>
        </div>

        {/* 🆕 Translate Captions */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">🌐 Translate Captions</h2>
          <select value={targetLang} onChange={e => setTargetLang(e.target.value)}
            className="input w-full mb-2" aria-label="Target language">
            {Object.entries(languages).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
          <button onClick={handleTranslate} disabled={translating} className="btn w-full" aria-label="Translate captions">
            {translating ? '⏳ Translating...' : `🌍 Translate to ${languages[targetLang]}`}
          </button>
          {translatedSrt && (
            <div className="mt-2 p-2 bg-slate-800 rounded text-xs max-h-40 overflow-y-auto whitespace-pre-wrap" role="status" aria-live="polite">
              {translatedSrt}
            </div>
          )}
        </div>

        {/* 🆕 Publish to Social */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">📱 Publish</h2>
          <div className="space-y-2">
            <button onClick={() => handlePublish('tiktok')} disabled={publishing}
              className="btn w-full bg-slate-800 hover:bg-slate-700" aria-label="Publish to TikTok">
              🎵 Publish to TikTok
            </button>
            <button onClick={() => handlePublish('youtube')} disabled={publishing}
              className="btn w-full bg-slate-800 hover:bg-slate-700" aria-label="Publish to YouTube">
              ▶️ Publish to YouTube
            </button>
            <button onClick={() => handlePublish('instagram')} disabled={publishing}
              className="btn w-full bg-slate-800 hover:bg-slate-700" aria-label="Publish to Instagram">
              📸 Publish to Instagram
            </button>
          </div>
          {publishResult && (
            <div className="mt-3 p-3 bg-slate-800 rounded text-xs" role="status" aria-live="polite">
              <p className="text-green-400 font-semibold mb-1">✅ {publishResult.status}</p>
              {publishResult.result?.instructions && (
                <ol className="list-decimal list-inside space-y-1 text-slate-300">
                  {Object.entries(publishResult.result.instructions).map(([k, v]) => (
                    <li key={k}>{v}</li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>

        {/* Styles */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">🎨 Style Learning</h2>
          <div className="flex gap-2 mb-3">
            <input className="input" placeholder="Style name..." value={styleName}
              onChange={e => setStyleName(e.target.value)}
              onKeyDown={handleStyleNameKeyDown}
              aria-label="Style name" />
            <button onClick={handleSaveStyle} className="btn" aria-label="Save style">Save</button>
          </div>
          {Object.keys(styles).length > 0 && (
            <div className="space-y-1">
              {Object.keys(styles).map(name => (
                <div key={name} className="flex gap-1">
                  <button onClick={() => applyStyle(name)}
                    className="flex-1 text-left text-sm py-1 px-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                    aria-label={`Apply style ${name}`}>
                    🎨 {name}
                  </button>
                  <button onClick={async () => {
                    if (!confirm(`Delete style "${name}"?`)) return;
                    await deleteStyle(name);
                    setStyles(prev => { const n = { ...prev }; delete n[name]; return n; });
                  }} className="px-2 text-red-400 hover:text-red-300 text-xs" aria-label={`Delete style ${name}`}>✕</button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Download */}
        <div className="card">
          <h2 className="font-semibold mb-3">📥 Download</h2>
          <a href={clipStreamUrl(id)} download className="btn w-full text-center block" aria-label="Download clip as MP4">
            ⬇ Download Clip MP4
          </a>
        </div>
      </div>
    </div>
  );
}
