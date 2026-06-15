import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import VideoDetail from './pages/VideoDetail'
import ClipEditor from './pages/ClipEditor'
import ThumbnailMaker from './pages/ThumbnailMaker'

function Nav() {
  const loc = useLocation();
  const link = (to, label) => (
    <Link to={to} className={`px-4 py-2 rounded-lg text-sm font-medium transition ${loc.pathname === to ? 'bg-violet-600 text-white' : 'text-slate-300 hover:bg-slate-700'}`}>
      {label}
    </Link>
  );
  return (
    <nav className="flex items-center gap-3 px-6 py-3 border-b border-slate-700 bg-slate-800/50">
      <Link to="/" className="text-xl font-bold text-violet-400 mr-4">🎬 ClipCraft</Link>
      {link('/', 'Library')}
      {link('/upload', 'Upload')}
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-900 text-slate-100">
        <Nav />
        <div className="p-6 max-w-7xl mx-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/video/:id" element={<VideoDetail />} />
            <Route path="/clip/:id" element={<ClipEditor />} />
            <Route path="/clip/:id/thumbnail" element={<ThumbnailMaker />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
