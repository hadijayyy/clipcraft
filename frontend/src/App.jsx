import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { lazy, Suspense } from 'react'
import ErrorBoundary from './ErrorBoundary.jsx'

const Dashboard = lazy(() => import('./pages/Dashboard'))
const Upload = lazy(() => import('./pages/Upload'))
const VideoDetail = lazy(() => import('./pages/VideoDetail'))
const ClipEditor = lazy(() => import('./pages/ClipEditor'))
const ThumbnailMaker = lazy(() => import('./pages/ThumbnailMaker'))

function Nav() {
  const loc = useLocation();
  const link = (to, label) => (
    <Link
      to={to}
      className={`px-4 py-2 rounded-lg text-sm font-medium transition ${loc.pathname === to ? 'bg-violet-600 text-white' : 'text-slate-300 hover:bg-slate-700'}`}
      aria-current={loc.pathname === to ? 'page' : undefined}
    >
      {label}
    </Link>
  );
  return (
    <nav className="flex items-center gap-3 px-6 py-3 border-b border-slate-700 bg-slate-800/50" aria-label="Main navigation">
      <Link to="/" className="text-xl font-bold text-violet-400 mr-4" aria-label="ClipCraft home">🎬 ClipCraft</Link>
      {link('/', 'Library')}
      {link('/upload', 'Upload')}
    </nav>
  );
}

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center py-20" role="status" aria-label="Loading">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">Loading...</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900 text-slate-100">
        <Nav />
        <div className="p-6 max-w-7xl mx-auto">
          <ErrorBoundary>
            <Suspense fallback={<LoadingFallback />}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/upload" element={<Upload />} />
                <Route path="/video/:id" element={<VideoDetail />} />
                <Route path="/clip/:id" element={<ClipEditor />} />
                <Route path="/clip/:id/thumbnail" element={<ThumbnailMaker />} />
              </Routes>
            </Suspense>
          </ErrorBoundary>
        </div>
      </div>
    </BrowserRouter>
  );
}
