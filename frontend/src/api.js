const API = import.meta.env.VITE_API_URL || 'https://43-157-200-187.sslip.io';

async function req(path, options = {}) {
  const url = `${API}${path}`;
  const res = await fetch(url, {
    headers: { 'Accept': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Upload a video file with real progress tracking via ReadableStream.
 * @param {File} file
 * @param {function} onProgress - callback(percent: number)
 * @param {AbortSignal} [signal] - optional AbortSignal
 */
export async function uploadVideo(file, onProgress, { signal } = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const form = new FormData();
    form.append('file', file);

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          if (onProgress) onProgress(100);
          resolve(data);
        } catch {
          reject(new Error('Invalid response from server'));
        }
      } else {
        reject(new Error(`Upload failed: HTTP ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
    xhr.addEventListener('abort', () => reject(new DOMException('Upload aborted', 'AbortError')));

    if (signal) {
      signal.addEventListener('abort', () => xhr.abort(), { once: true });
    }

    xhr.open('POST', `${API}/api/upload`);
    xhr.send(form);
  });
}

export async function importYoutube(url, { signal } = {}) {
  const form = new FormData();
  form.append('url', url);
  return req('/api/youtube', { method: 'POST', body: form, signal });
}

// ─── YouTube Cookies ─────────────────────────────────────
export async function uploadYoutubeCookies(file, { signal } = {}) {
  const form = new FormData();
  form.append('cookies', file);
  return req('/api/youtube/cookies', { method: 'POST', body: form, signal });
}

export async function deleteYoutubeCookies({ signal } = {}) {
  return req('/api/youtube/cookies', { method: 'DELETE', signal });
}

export async function importYoutubeDirect(url, { signal } = {}) {
  const form = new FormData();
  form.append('url', url);
  return req('/api/youtube-direct', { method: 'POST', body: form, signal });
}

export async function processDirect(id, { signal } = {}) {
  return req(`/api/process-direct/${id}`, { method: 'POST', signal });
}

export async function clipDirect(id, start, end, { signal } = {}) {
  const form = new FormData();
  form.append('start', String(start));
  form.append('end', String(end));
  return req(`/api/clip-direct/${id}`, { method: 'POST', body: form, signal });
}

export async function processVideo(id, { signal } = {}) {
  return req(`/api/process/${id}`, { method: 'POST', signal });
}

export async function getVideos({ limit = 50, offset = 0, q, source, status, signal } = {}) {
  const params = new URLSearchParams();
  params.set('limit', limit);
  params.set('offset', offset);
  if (q) params.set('q', q);
  if (source) params.set('source', source);
  if (status) params.set('status', status);
  return req(`/api/videos?${params.toString()}`, { signal });
}

export async function searchVideos(query, { signal } = {}) {
  return req(`/api/videos?q=${encodeURIComponent(query)}`, { signal });
}

// ─── Smart Crop ──────────────────────────────────────────
export async function smartCropClip(videoId, start, end, quality = 'balanced', { signal } = {}) {
  const form = new FormData();
  form.append('start', String(start));
  form.append('end', String(end));
  form.append('quality', quality);
  return req(`/api/clip/smart/${videoId}`, { method: 'POST', body: form, signal });
}

// ─── Viral Analysis ──────────────────────────────────────
export async function analyzeViral(videoId, { signal } = {}) {
  return req(`/api/analyze/viral/${videoId}`, { method: 'POST', signal });
}

// ─── Export Formats ──────────────────────────────────────
export async function getExportFormats({ signal } = {}) {
  return req('/api/export/formats', { signal });
}

export async function exportClip(clipId, format = '9:16', { signal } = {}) {
  const form = new FormData();
  form.append('format', format);
  return req(`/api/clip/export/${clipId}`, { method: 'POST', body: form, signal });
}

// ─── Translation ─────────────────────────────────────────
export async function getSupportedLanguages({ signal } = {}) {
  return req('/api/translate/languages', { signal });
}

export async function translateClip(clipId, targetLang = 'id', { signal } = {}) {
  const form = new FormData();
  form.append('target_lang', targetLang);
  return req(`/api/clip/${clipId}/translate`, { method: 'POST', body: form, signal });
}

// ─── Social Publishing ───────────────────────────────────
export async function publishClip(clipId, { platform, title = '', description = '', tags = '' }, { signal } = {}) {
  const form = new FormData();
  form.append('platform', platform);
  form.append('title', title);
  form.append('description', description);
  form.append('tags', tags);
  return req(`/api/publish/${clipId}`, { method: 'POST', body: form, signal });
}

// ─── Background Processing ───────────────────────────────
export async function processVideoBackground(id, { signal } = {}) {
  return req(`/api/process-bg/${id}`, { method: 'POST', signal });
}

export async function getVideo(id, { signal } = {}) {
  return req(`/api/videos/${id}`, { signal });
}

export async function deleteVideo(id, { signal } = {}) {
  return req(`/api/videos/${id}`, { method: 'DELETE', signal });
}

export function videoStreamUrl(id) {
  return `${API}/api/video/${id}/stream`;
}

export async function autoClip(id, { signal } = {}) {
  return req(`/api/clip/auto/${id}`, { method: 'POST', signal });
}

export async function manualClip(id, start, end, { signal } = {}) {
  const form = new FormData();
  form.append('start', String(start));
  form.append('end', String(end));
  return req(`/api/clip/manual/${id}`, { method: 'POST', body: form, signal });
}

export async function splitClip(id, targetLength, overlap = 0.5, { signal } = {}) {
  const form = new FormData();
  form.append('target_length', String(targetLength));
  form.append('overlap', String(overlap));
  return req(`/api/clip/split/${id}`, { method: 'POST', body: form, signal });
}

export async function getClips(videoId, { signal } = {}) {
  return req(`/api/clips/${videoId}`, { signal });
}

export async function getClip(id, { signal } = {}) {
  return req(`/api/clip/${id}`, { signal });
}

export function clipStreamUrl(id) {
  return `${API}/api/clip/${id}/stream`;
}

export async function getClipSrt(id, { signal } = {}) {
  return req(`/api/clip/${id}/srt`, { signal });
}

export async function saveSubtitles(id, subtitlesJson, { signal } = {}) {
  const form = new FormData();
  form.append('subtitles', subtitlesJson);
  return req(`/api/clip/${id}/subtitles`, { method: 'POST', body: form, signal });
}

export async function saveOverlays(id, overlaysJson, { signal } = {}) {
  const form = new FormData();
  form.append('overlays', overlaysJson);
  return req(`/api/clip/${id}/overlays`, { method: 'POST', body: form, signal });
}

export async function deleteClip(id, { signal } = {}) {
  return req(`/api/clip/${id}`, { method: 'DELETE', signal });
}

export async function generateThumbnail(clipId, timeSec = 0.5, { signal } = {}) {
  const form = new FormData();
  form.append('time_sec', String(timeSec));
  return req(`/api/thumbnail/${clipId}`, { method: 'POST', body: form, signal });
}

export function thumbnailUrl(clipId) {
  return `${API}/api/thumbnail/${clipId}/image`;
}

export async function getStyles({ signal } = {}) {
  return req('/api/style', { signal });
}

export async function saveStyle(name, settings = {}, { signal } = {}) {
  const form = new FormData();
  form.append('name', name);
  form.append('settings', JSON.stringify(settings));
  return req('/api/style/save', { method: 'POST', body: form, signal });
}

export async function deleteStyle(name, { signal } = {}) {
  return req(`/api/style/${name}`, { method: 'DELETE', signal });
}
