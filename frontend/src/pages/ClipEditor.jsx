import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getClip, clipStreamUrl, getClipSrt, saveSubtitles, saveOverlays, getStyles, saveStyle } from '../api';

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

  const videoRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    const load = async () => {
      const c = await getClip(id);
      setClip(c);
      if (c.overlays) {
        try { setOverlays(JSON.parse(c.overlays)); } catch {}
      }
      const srt = await getClipSrt(id);
      setSrtData(srt);
      if (srt?.srt) setSubtitleText(srt.srt);
      const st = await getStyles();
      setStyles(st || {});
      setLoading(false);
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

  const handleMouseDown = (idx, e) => {
    setDragIdx(idx);
  };

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
    await saveStyle(styleName, {
      overlayCount: overlays.length,
      fontSizes: overlays.map(o => o.fontSize),
      colors: overlays.map(o => o.color),
      bgColors: overlays.map(o => o.bgColor),
    });
    setStyles({ ...styles, [styleName]: {} });
    alert(`Style "${styleName}" saved!`);
    setStyleName('');
  };

  const applyStyle = (name) => {
    const s = styles[name]?.settings;
    if (!s) return;
    alert(`Style "${name}" applied! (Customize overlays manually from here)`);
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
            <Link to={`/clip/${id}/thumbnail`} className="btn text-sm bg-emerald-600 hover:bg-emerald-500">
              🖼 Make Thumbnail
            </Link>
          </div>

          <div ref={containerRef} className="relative bg-black rounded-lg overflow-hidden" style={{ maxWidth: '400px', margin: '0 auto' }}>
            <video ref={videoRef} src={clipStreamUrl(id)} controls className="w-full aspect-[9/16]" />

            {/* Draggable Text Overlays */}
            {overlays.map((ov, i) => (
              <div
                key={ov.id}
                onMouseDown={(e) => handleMouseDown(i, e)}
                style={{
                  position: 'absolute',
                  left: `${ov.x}%`,
                  top: `${ov.y}%`,
                  transform: 'translate(-50%, -50%)',
                  fontSize: `${ov.fontSize}px`,
                  color: ov.color,
                  backgroundColor: ov.bgColor,
                  padding: '4px 12px',
                  borderRadius: '6px',
                  cursor: dragIdx === i ? 'grabbing' : 'grab',
                  userSelect: 'none',
                  whiteSpace: 'nowrap',
                  zIndex: 10,
                }}
              >
                {ov.text}
                <button
                  onClick={() => removeOverlay(i)}
                  className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 text-xs flex items-center justify-center"
                  style={{ zIndex: 11 }}
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          {/* Add Overlay Form */}
          <div className="mt-4 flex gap-2">
            <input className="input flex-1" placeholder="Text to show on video..." value={newText} onChange={e => setNewText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && addOverlay()}
            />
            <button onClick={addOverlay} className="btn">Add Text</button>
          </div>

          {/* Overlay Style Controls */}
          {overlays.length > 0 && (
            <div className="mt-3 grid grid-cols-3 gap-2">
              {overlays.map((ov, i) => (
                <div key={ov.id} className="bg-slate-800 p-2 rounded text-xs">
                  <p className="truncate text-slate-300 mb-1">{ov.text}</p>
                  <input type="range" min="12" max="72" value={ov.fontSize}
                    onChange={e => {
                      const n = [...overlays];
                      n[i] = { ...n[i], fontSize: Number(e.target.value) };
                      setOverlays(n);
                    }}
                    className="w-full"
                  />
                  <input type="color" value={ov.color}
                    onChange={e => {
                      const n = [...overlays];
                      n[i] = { ...n[i], color: e.target.value };
                      setOverlays(n);
                    }}
                    className="w-full h-6 rounded mt-1"
                  />
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
          <textarea
            className="input font-mono text-xs h-60"
            value={subtitleText}
            onChange={e => setSubtitleText(e.target.value)}
          />
          <button onClick={handleSaveSubtitles} className="btn w-full mt-2">💾 Save Subtitles</button>
        </div>

        {/* Styles */}
        <div className="card mb-4">
          <h2 className="font-semibold mb-3">🎨 Style Learning</h2>

          <p className="text-xs text-slate-400 mb-2">Save current overlay settings as a style:</p>
          <div className="flex gap-2 mb-3">
            <input className="input" placeholder="Style name..." value={styleName} onChange={e => setStyleName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSaveStyle()}
            />
            <button onClick={handleSaveStyle} className="btn">Save</button>
          </div>

          {Object.keys(styles).length > 0 && (
            <div>
              <p className="text-xs text-slate-400 mb-2">Saved styles:</p>
              <div className="space-y-1">
                {Object.keys(styles).map(name => (
                  <button key={name} onClick={() => applyStyle(name)}
                    className="w-full text-left text-sm py-1 px-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300">
                    🎨 {name}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Download */}
        <div className="card">
          <h2 className="font-semibold mb-3">📥 Download</h2>
          <a href={clipStreamUrl(id)} download className="btn w-full text-center block">
            ⬇ Download Clip MP4
          </a>
          <Link to={`/clip/${id}/thumbnail`} className="btn w-full text-center block mt-2 bg-emerald-600 hover:bg-emerald-500">
            🖼 Create Thumbnail
          </Link>
        </div>
      </div>
    </div>
  );
}
