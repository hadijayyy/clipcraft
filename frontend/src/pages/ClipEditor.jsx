import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  getClip, clipStreamUrl, getClipSrt, saveSubtitles, saveOverlays,
  getStyles, saveStyle, deleteStyle, deleteClip,
  exportClip, getExportFormats, translateClip, getSupportedLanguages, publishClip
} from '../api';

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

  useEffect(() => {
    const load = async () => {
      try {
        const [c, formats, langs] = await Promise.all([
          getClip(id),
          getExportFormats(),
          getSupportedLanguages()
        ]);
        setClip(c);
        setExportFormats(formats.formats || {});
        setLanguages(langs.languages || {});
        if (c.overlays) {
          try { setOverlays(JSON.parse(c.overlays)); } catch {}
        }
        const srt = await getClipSrt(id);
        setSrtData(srt);
        if (srt?.srt) setSubtitleText(srt.srt);
        const st = await getStyles();
        setStyles(st || {});
      } catch (e) {
        console.error('Failed to load clip:', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  const handleSaveOverlays = async () => {
    await saveOverlays(id, JSON.stringify(overlays));
    alert('Overlays saved!');
  };

  const handleSaveSubtitles = async () => {
    await saveSubtitles(id, subtitleText);
    alert('Subtitles saved!');
  };

  const addOverlay = () => {
    if (!newText.trim()) return;
    setOverlays([...overlays, {
      id: Date.now(),
      text: newText,
      x: 50, y: 50,
      fontSize: 24,
      color: '#ffffff',
      bgColor: 'rgba(0,0,0,0.5)',
    }]);
    setNewText('');
  };

  const removeOverlay = (idx) => {
    setOverlays(overlays.filter((_, i) => i !== idx));
  };

  const handleMouseDown = (idx) => setDragIdx(idx);

  const handleMouseMove = (e) => {
    if (dragIdx === null || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    const newOv = [...overlays];
    newOv[dragIdx] = { ...newOv[dragIdx], x: Math.max(0, Math.min(100, x)), y: Math.max(0, Math.min(100, y)) };
    setOverlays(newOv);
  };

  const handleMouseUp = () => setDragIdx(null);

  const handleSaveStyle = async () => {
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
  };

  const applyStyle = (name) => {
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
  };

  // ─── Export ────────────────────────────────────────────
  const handleExport = async () => {
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
  };

  // ─── Translate ─────────────────────────────────────────
  const handleTranslate = async () => {
    setTranslating(true);
    try {
      const result = await translateClip(id, targetLang);
      setTranslatedSrt(result.translated_srt || '(no speech detected)');
      alert(`Translated to ${languages[targetLang] || targetLang}`);
    } catch (e) {
      alert('Translation failed: ' + e.message);
    }
    setTranslating(false);
  };

  // ─── Publish ───────────────────────────────────────────
  const handlePublish = async (platform) => {
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
  };

  const handleDeleteClip = async () => {
    if (!confirm('Delete this clip permanently?')) return;
    await deleteClip(id);
    window.location.href = '/';
  };

  if (loading) return <p className="text-slate-400">Loading editor...</p>;
  if (!clip) return <p className="text-red-400">Clip not found</p>;

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
              <Link to={`/clip/${id}/thumbnail`} className="btn text-sm bg-emerald-600 hover:bg-emerald-500">
                🖼 Thumbnail
              </Link>
              <button onClick={handleDeleteClip} className="btn text-sm bg-red-600 hover:bg-red-500">
                🗑 Delete
              </button>
            </div>
          </div>

          <div ref={containerRef} className="relative bg-black rounded-lg overflow-hidden" style={{ maxWidth: '400px', margin: '0 auto' }}>
            <video ref={videoRef} src={clipStreamUrl(id)} controls className="w-full aspect-[9/16]" />

            {/* Draggable Text Overlays */}
            {overlays.map((ov, i) => (
              <div
                key={ov.id}
                onMouseDown={() => handleMouseDown(i)}
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
                  style={{ zIndex: 11 }}>×</button>
              </div>
            ))}
          </div>

          {/* Add Overlay */}
          <div className="mt-4 flex gap-2">
            <input className="input flex-1" placeholder="Text to show on video..." value={newText}
              onChange={e => setNewText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addOverlay()} />
            <button onClick={addOverlay} className="btn">Add Text</button>
          </div>

          {/* Overlay Controls */}
          {overlays.length > 0 && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {overlays.map((ov, i) => (
                <div key={ov.id} className="bg-slate-800 p-2 rounded text-xs">
                  <p className="truncate text-slate-300 mb-1">{ov.text}</p>
                  <input type="range" min="12" max="72" value={ov.fontSize}
                    onChange={e => { const n = [...overlays]; n[i] = { ...n[i], fontSize: Number(e.target.value) }; setOverlays(n); }}
                    className="w-full" />
                  <input type="color" value={ov.color}
                    onChange={e => { const n = [...overlays]; n[i] = { ...n[i], color: e.target.value }; setOverlays(n); }}
                    className="w-full h-6 rounded mt-1" />
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2 mt-3">
            <button onClick={handleSaveOverlays} className="btn flex-1">💾 Save Overlays</button>
          </div>
        </div>
      </div>

      {/* Right Sidebar */}
      <div>
        {/* Subtitles */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">💬 Subtitles</h2>
          <textarea className="input font-mono text-xs h-40" value={subtitleText}
            onChange={e => setSubtitleText(e.target.value)} />
          <button onClick={handleSaveSubtitles} className="btn w-full mt-2">💾 Save Subtitles</button>
        </div>

        {/* 🆕 Export Format */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">📐 Export Format</h2>
          <select value={exportFormat} onChange={e => setExportFormat(e.target.value)}
            className="input w-full mb-2">
            {Object.entries(exportFormats).map(([key, fmt]) => (
              <option key={key} value={key}>{key} — {fmt.label}</option>
            ))}
          </select>
          <button onClick={handleExport} disabled={exporting} className="btn w-full">
            {exporting ? '⏳ Exporting...' : `📤 Export ${exportFormat}`}
          </button>
        </div>

        {/* 🆕 Translate Captions */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">🌐 Translate Captions</h2>
          <select value={targetLang} onChange={e => setTargetLang(e.target.value)}
            className="input w-full mb-2">
            {Object.entries(languages).map(([code, name]) => (
              <option key={code} value={code}>{name}</option>
            ))}
          </select>
          <button onClick={handleTranslate} disabled={translating} className="btn w-full">
            {translating ? '⏳ Translating...' : `🌍 Translate to ${languages[targetLang]}`}
          </button>
          {translatedSrt && (
            <div className="mt-2 p-2 bg-slate-800 rounded text-xs max-h-40 overflow-y-auto whitespace-pre-wrap">
              {translatedSrt}
            </div>
          )}
        </div>

        {/* 🆕 Publish to Social */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">📱 Publish</h2>
          <div className="space-y-2">
            <button onClick={() => handlePublish('tiktok')} disabled={publishing}
              className="btn w-full bg-slate-800 hover:bg-slate-700">
              🎵 Publish to TikTok
            </button>
            <button onClick={() => handlePublish('youtube')} disabled={publishing}
              className="btn w-full bg-slate-800 hover:bg-slate-700">
              ▶️ Publish to YouTube
            </button>
            <button onClick={() => handlePublish('instagram')} disabled={publishing}
              className="btn w-full bg-slate-800 hover:bg-slate-700">
              📸 Publish to Instagram
            </button>
          </div>
          {publishResult && (
            <div className="mt-3 p-3 bg-slate-800 rounded text-xs">
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
              onKeyDown={e => e.key === 'Enter' && handleSaveStyle()} />
            <button onClick={handleSaveStyle} className="btn">Save</button>
          </div>
          {Object.keys(styles).length > 0 && (
            <div className="space-y-1">
              {Object.keys(styles).map(name => (
                <div key={name} className="flex gap-1">
                  <button onClick={() => applyStyle(name)}
                    className="flex-1 text-left text-sm py-1 px-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300">
                    🎨 {name}
                  </button>
                  <button onClick={async () => {
                    if (!confirm(`Delete style "${name}"?`)) return;
                    await deleteStyle(name);
                    setStyles(prev => { const n = { ...prev }; delete n[name]; return n; });
                  }} className="px-2 text-red-400 hover:text-red-300 text-xs">✕</button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Download */}
        <div className="card">
          <h2 className="font-semibold mb-3">📥 Download</h2>
          <a href={clipStreamUrl(id)} download className="btn w-full text-center block">
            ⬇ Download Clip MP4
          </a>
        </div>
      </div>
    </div>
  );
}
