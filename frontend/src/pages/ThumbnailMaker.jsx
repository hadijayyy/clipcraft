import { useState, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { clipStreamUrl, generateThumbnail, thumbnailUrl } from '../api';

export default function ThumbnailMaker() {
  const { id } = useParams();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [seekTime, setSeekTime] = useState(0.5);
  const [thumbUrl, setThumbUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [clipDuration, setClipDuration] = useState(60);

  const handleSeek = useCallback((t) => {
    setSeekTime(t);
    if (videoRef.current) {
      videoRef.current.currentTime = t;
    }
  }, []);

  const captureFrame = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    // Seek to exact time
    video.currentTime = seekTime;
    await new Promise(resolve => {
      video.addEventListener('seeked', resolve, { once: true });
      setTimeout(resolve, 2000);
    });

    canvas.width = video.videoWidth || 720;
    canvas.height = video.videoHeight || 1280;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    // Save to backend
    setLoading(true);
    try {
      const data = await generateThumbnail(id, seekTime);
      setThumbUrl(thumbnailUrl(id) + '?t=' + Date.now());
    } catch (e) {
      alert('Error: ' + e.message);
    }
    setLoading(false);
  }, [id, seekTime]);

  const downloadThumb = useCallback(() => {
    if (!thumbUrl) return;
    const link = document.createElement('a');
    link.download = `clip_${id}_thumb.jpg`;
    link.href = thumbUrl;
    link.click();
  }, [id, thumbUrl]);

  const handleLoadedMetadata = useCallback(() => {
    if (videoRef.current) {
      videoRef.current.currentTime = seekTime;
      setClipDuration(Math.ceil(videoRef.current.duration) || 60);
    }
  }, [seekTime]);

  return (
    <div className="max-w-2xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">🖼 Thumbnail Maker</h1>
        <Link to={`/clip/${id}`} className="btn" aria-label="Back to editor">← Back to Editor</Link>
      </div>

      <div className="card mb-4">
        <div className="relative bg-black rounded-lg overflow-hidden mb-4" style={{ maxWidth: '360px', margin: '0 auto' }}>
          <video
            ref={videoRef}
            src={clipStreamUrl(id)}
            className="w-full aspect-[9/16]"
            controls
            preload="auto"
            onLoadedMetadata={handleLoadedMetadata}
            aria-label="Clip video for thumbnail capture"
          />
        </div>

        <div className="mb-4">
          <label className="text-sm text-slate-400 mb-1 block" htmlFor="seek-slider">Seek to second: {seekTime.toFixed(1)}s</label>
          <input
            id="seek-slider"
            type="range"
            min="0"
            max={clipDuration}
            step="0.1"
            value={seekTime}
            onChange={e => handleSeek(Number(e.target.value))}
            className="w-full"
            aria-label={`Seek to ${seekTime.toFixed(1)} seconds`}
          />
          <div className="flex justify-between text-xs text-slate-500 mt-1">
            <span>0s</span>
            <span>{clipDuration}s</span>
          </div>
        </div>

        <div className="flex gap-2">
          <button onClick={captureFrame} disabled={loading} className="btn flex-1 text-center" aria-label="Capture frame as thumbnail">
            {loading ? 'Generating...' : '📸 Capture Frame'}
          </button>
          {thumbUrl && (
            <button onClick={downloadThumb} className="btn bg-emerald-600 hover:bg-emerald-500 flex-1 text-center" aria-label="Download thumbnail">
              ⬇ Download
            </button>
          )}
        </div>
      </div>

      <canvas ref={canvasRef} className="hidden" aria-hidden="true" />

      {thumbUrl && (
        <div className="card text-center">
          <h2 className="font-semibold mb-3">Generated Thumbnail</h2>
          <img src={thumbUrl} alt="Generated thumbnail" className="rounded-lg max-w-[360px] mx-auto mb-3 shadow-lg" />
          <a href={thumbUrl} download className="btn" aria-label="Download thumbnail as JPEG">⬇ Download JPEG</a>
        </div>
      )}
    </div>
  );
}
