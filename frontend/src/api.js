const API = import.meta.env.VITE_API_URL || 'http://localhost:8001';

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

export async function uploadVideo(file, onProgress) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${API}/api/upload`, { method: 'POST', body: form });
  const data = await res.json();
  if (onProgress) onProgress(100);
  return data;
}

export async function importYoutube(url) {
  const form = new FormData();
  form.append('url', url);
  return req('/api/youtube', { method: 'POST', body: form });
}

export async function importYoutubeDirect(url) {
  const form = new FormData();
  form.append('url', url);
  return req('/api/youtube-direct', { method: 'POST', body: form });
}

export async function processDirect(id) {
  return req(`/api/process-direct/${id}`, { method: 'POST' });
}

export async function clipDirect(id, start, end) {
  const form = new FormData();
  form.append('start', String(start));
  form.append('end', String(end));
  return req(`/api/clip-direct/${id}`, { method: 'POST', body: form });
}

export async function processVideo(id) {
  return req(`/api/process/${id}`, { method: 'POST' });
}

export async function getVideos() {
  return req('/api/videos');
}

export async function getVideo(id) {
  return req(`/api/videos/${id}`);
}

export async function deleteVideo(id) {
  return req(`/api/videos/${id}`, { method: 'DELETE' });
}

export function videoStreamUrl(id) {
  return `${API}/api/video/${id}/stream`;
}

export async function autoClip(id) {
  return req(`/api/clip/auto/${id}`, { method: 'POST' });
}

export async function manualClip(id, start, end) {
  const form = new FormData();
  form.append('start', String(start));
  form.append('end', String(end));
  return req(`/api/clip/manual/${id}`, { method: 'POST', body: form });
}

export async function splitClip(id, targetLength, overlap = 0.5) {
  const form = new FormData();
  form.append('target_length', String(targetLength));
  form.append('overlap', String(overlap));
  return req(`/api/clip/split/${id}`, { method: 'POST', body: form });
}

export async function getClips(videoId) {
  return req(`/api/clips/${videoId}`);
}

export async function getClip(id) {
  return req(`/api/clip/${id}`);
}

export function clipStreamUrl(id) {
  return `${API}/api/clip/${id}/stream`;
}

export async function getClipSrt(id) {
  return req(`/api/clip/${id}/srt`);
}

export async function saveSubtitles(id, subtitlesJson) {
  const form = new FormData();
  form.append('subtitles', subtitlesJson);
  return req(`/api/clip/${id}/subtitles`, { method: 'POST', body: form });
}

export async function saveOverlays(id, overlaysJson) {
  const form = new FormData();
  form.append('overlays', overlaysJson);
  return req(`/api/clip/${id}/overlays`, { method: 'POST', body: form });
}

export async function deleteClip(id) {
  return req(`/api/clip/${id}`, { method: 'DELETE' });
}

export async function generateThumbnail(clipId, timeSec = 0.5) {
  const form = new FormData();
  form.append('time_sec', String(timeSec));
  return req(`/api/thumbnail/${clipId}`, { method: 'POST', body: form });
}

export function thumbnailUrl(clipId) {
  return `${API}/api/thumbnail/${clipId}/image`;
}

export async function getStyles() {
  return req('/api/style');
}

export async function saveStyle(name, settings = {}) {
  const form = new FormData();
  form.append('name', name);
  form.append('settings', JSON.stringify(settings));
  return req('/api/style/save', { method: 'POST', body: form });
}

export async function deleteStyle(name) {
  return req(`/api/style/${name}`, { method: 'DELETE' });
}
