import { Routes, Route } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import StatusPage from './pages/StatusPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-3">
          <h1 className="text-xl font-semibold text-gray-800">
            金融财报智能分析平台
          </h1>
        </div>
      </header>
      <main className="max-w-5xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/status/:sessionId" element={<StatusPage />} />
        </Routes>
      </main>
    </div>
  )
}
