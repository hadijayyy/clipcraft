import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadVideo, importYoutube, importYoutubeDirect, uploadYoutubeCookies } from '../api';

export default function Upload() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('file');
  const [file, setFile] = useState(null);
  const [cookiesFile, setCookiesFile] = useState(null);
  const [ytUrl, setYtUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState('');
  const [cookiesSaved, setCookiesSaved] = useState(false);

  const abortRef = useRef(null);

  const handleFileUpload = useCallback(async () => {
    if (!file) return;
    setLoading(true);
    setProgress(0);
    setStatus('Uploading...');
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const data = await uploadVideo(file, (p) => setProgress(p), { signal: controller.signal });
      setStatus('Processing...');
      navigate(`/video/${data.id}`);
    } catch (e) {
      if (e.name !== 'AbortError') {
        setStatus('Error: ' + e.message);
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [file, navigate]);

  const handleUploadCookies = useCallback(async () => {
    if (!cookiesFile) return;
    setLoading(true);
    setStatus('Uploading cookies...');
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      await uploadYoutubeCookies(cookiesFile, { signal: controller.signal });
      setCookiesSaved(true);
      setStatus('Cookies saved! Now paste YouTube URL and import.');
    } catch (e) {
      if (e.name !== 'AbortError') {
        setStatus('Error: ' + e.message);
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [cookiesFile]);

  const handleYtImport = useCallback(async () => {
    if (!ytUrl.trim()) return;
    setLoading(true);
    setProgress(0);
    setStatus('Downloading from YouTube (720p-1080p)...');
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const data = await importYoutube(ytUrl.trim(), { signal: controller.signal });
      setStatus('Processing...');
      navigate(`/video/${data.id}`);
    } catch (e) {
      if (e.name !== 'AbortError') {
        const msg = e.message || '';
        if (msg.includes('403') || msg.includes('bot')) {
          setStatus('⚠️ YouTube bot detection! Upload cookies.txt above first.');
        } else {
          setStatus('Error: ' + msg);
        }
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [ytUrl, navigate]);

  const handleYtDirect = useCallback(async () => {
    if (!ytUrl.trim()) return;
    setLoading(true);
    setStatus('Connecting to YouTube...');
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const data = await importYoutubeDirect(ytUrl.trim(), { signal: controller.signal });
      setStatus('Transcribing audio...');
      navigate(`/video/${data.id}`);
    } catch (e) {
      if (e.name !== 'AbortError') {
        const msg = e.message || '';
        if (msg.includes('403') || msg.includes('bot')) {
          setStatus('⚠️ YouTube bot detection! Upload cookies.txt above first.');
        } else {
          setStatus('Error: ' + msg);
        }
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  }, [ytUrl, navigate]);

  return (
    <div className="max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">🎬 Import Video</h1>

      {/* YouTube Cookies (always visible) */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold text-sm">🍪 YouTube Cookies</h3>
          {cookiesSaved && <span className="text-xs text-green-400">✓ Saved</span>}
        </div>
        <p className="text-xs text-slate-400 mb-3">
          If YouTube blocks download, export cookies from your browser and upload here.
          <a href="https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc" target="_blank" rel="noreferrer" className="text-violet-400 hover:underline ml-1" aria-label="Get cookies extension">
            Get extension →
          </a>
        </p>
        <div className="flex gap-2">
          <label className="flex-1">
            <div className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 cursor-pointer hover:border-violet-500 truncate">
              {cookiesFile ? `✓ ${cookiesFile.name}` : '📄 Select cookies.txt'}
            </div>
            <input type="file" accept=".txt" className="hidden" onChange={e => setCookiesFile(e.target.files[0])} aria-label="Select cookies.txt file" />
          </label>
          <button onClick={handleUploadCookies} disabled={!cookiesFile || loading} className="btn text-sm" aria-label="Upload cookies file">
            Upload
          </button>
        </div>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-1 mb-6 bg-slate-800 rounded-lg p-1" role="tablist" aria-label="Import method">
        <button
          onClick={() => setTab('file')}
          className={`flex-1 py-2 rounded-md text-sm font-medium transition ${tab === 'file' ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'}`}
          role="tab"
          aria-selected={tab === 'file'}
          aria-controls="tab-panel-file"
        >
          📁 Upload File
        </button>
        <button
          onClick={() => setTab('youtube')}
          className={`flex-1 py-2 rounded-md text-sm font-medium transition ${tab === 'youtube' ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'}`}
          role="tab"
          aria-selected={tab === 'youtube'}
          aria-controls="tab-panel-youtube"
        >
          📺 YouTube URL
        </button>
        <button
          onClick={() => setTab('direct')}
          className={`flex-1 py-2 rounded-md text-sm font-medium transition ${tab === 'direct' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'}`}
          role="tab"
          aria-selected={tab === 'direct'}
          aria-controls="tab-panel-direct"
        >
          ⚡ Direct Link
        </button>
      </div>

      <div className="card">
        {tab === 'file' && (
          <div id="tab-panel-file" role="tabpanel" aria-label="File upload">
            <div
              className="border-2 border-dashed border-slate-600 rounded-lg p-12 text-center cursor-pointer hover:border-violet-500 transition"
              onClick={() => document.getElementById('fileInput').click()}
              onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); document.getElementById('fileInput').click(); }}}
              role="button"
              tabIndex={0}
              aria-label="Click to select a video file"
            >
              {file ? (
                <div>
                  <p className="text-lg font-medium mb-1">{file.name}</p>
                  <p className="text-sm text-slate-400">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                </div>
              ) : (
                <div>
                  <p className="text-4xl mb-3">📂</p>
                  <p className="text-slate-300">Click to select a video file</p>
                  <p className="text-sm text-slate-500 mt-1">MP4, MOV, AVI, MKV — max 2GB</p>
                </div>
              )}
              <input id="fileInput" type="file" accept="video/*" className="hidden" onChange={e => setFile(e.target.files[0])} aria-label="Video file input" />
            </div>

            {progress > 0 && progress < 100 && (
              <div className="mt-4" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} aria-label="Upload progress">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Uploading... {progress}%</span>
                </div>
                <div className="bg-slate-700 rounded-full h-2">
                  <div className="bg-violet-500 h-2 rounded-full transition-all" style={{ width: `${progress}%` }} />
                </div>
              </div>
            )}

            <button onClick={handleFileUpload} disabled={!file || loading} className="btn w-full mt-4 text-center" aria-label="Upload and process video">
              {loading ? status || 'Uploading...' : 'Upload & Process'}
            </button>
          </div>
        )}

        {tab === 'youtube' && (
          <div id="tab-panel-youtube" role="tabpanel" aria-label="YouTube import">
            <p className="text-sm text-slate-400 mb-3">Download full video (720p-1080p) then clip. Saved to library.</p>
            <input
              className="input mb-4"
              placeholder="https://youtube.com/watch?v=..."
              value={ytUrl}
              onChange={e => setYtUrl(e.target.value)}
              aria-label="YouTube video URL"
            />
            <button onClick={handleYtImport} disabled={!ytUrl.trim() || loading} className="btn w-full text-center" aria-label="Download and process YouTube video">
              {loading ? status || 'Downloading...' : '📥 Download & Process'}
            </button>
          </div>
        )}

        {tab === 'direct' && (
          <div id="tab-panel-direct" role="tabpanel" aria-label="Direct link import">
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 mb-4">
              <p className="text-sm text-emerald-300 font-medium mb-1">⚡ Direct Link Mode</p>
              <p className="text-xs text-slate-400">
                Paste YouTube link → transcribe audio only → clip directly from URL.
                <strong className="text-emerald-300"> No full video download.</strong> Saves storage!
              </p>
            </div>
            <input
              className="input mb-4"
              placeholder="https://youtube.com/watch?v=..."
              value={ytUrl}
              onChange={e => setYtUrl(e.target.value)}
              aria-label="YouTube video URL for direct import"
            />
            <button onClick={handleYtDirect} disabled={!ytUrl.trim() || loading} className="btn w-full text-center bg-emerald-600 hover:bg-emerald-500" aria-label="Import YouTube video directly">
              {loading ? status || 'Connecting...' : '⚡ Import Direct'}
            </button>
          </div>
        )}
      </div>

      {status && loading && (
        <div className="card mt-4 text-center" role="status" aria-live="polite">
          <p className="text-slate-300">{status}</p>
          <p className="text-sm text-slate-500 mt-1">
            {tab === 'direct' ? 'Only downloading audio (~5MB)' : 'This may take a few minutes for long videos'}
          </p>
        </div>
      )}

      {status && !loading && status.includes('Error') && (
        <div className="card mt-4 text-center border-red-500/30" role="alert">
          <p className="text-red-400">{status}</p>
        </div>
      )}
    </div>
  );
}
