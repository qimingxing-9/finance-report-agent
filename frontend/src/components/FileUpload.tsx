import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadPDF } from '../api/client'

const MAX_SIZE = 20 * 1024 * 1024

export default function FileUpload() {
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleFile(file: File) {
    setError(null)

    if (!file.name.endsWith('.pdf') && file.type !== 'application/pdf') {
      setError('文件格式不支持，请上传 PDF')
      return
    }
    if (file.size > MAX_SIZE) {
      setError('文件大小超过 20MB 限制')
      return
    }

    setUploading(true)
    try {
      const res = await uploadPDF(file)
      if (res.code !== 0) {
        setError(res.msg)
      } else {
        navigate(`/status/${res.data!.session_id}`)
      }
    } catch (e) {
      setError('上传失败，请重试')
    } finally {
      setUploading(false)
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <div className="max-w-xl mx-auto">
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors
          ${dragging ? 'border-blue-400 bg-blue-50' : 'border-gray-300 bg-white hover:border-gray-400'}`}
      >
        <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M7 16a4 4 0 01-.88-7.9A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <p className="mt-4 text-sm text-gray-600">
          {uploading ? '上传中...' : '点击或拖拽 PDF 文件到此处'}
        </p>
        <p className="mt-1 text-xs text-gray-400">仅支持 PDF 格式，最大 20MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) handleFile(file)
          }}
        />
      </div>
      {error && (
        <p className="mt-3 text-sm text-red-600 text-center">{error}</p>
      )}
    </div>
  )
}
