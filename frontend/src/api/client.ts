import axios from 'axios'

const api = axios.create({ baseURL: '/api/report' })

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T | null
}

export interface UploadResult {
  session_id: string
  status: string
}

export interface StatusResult {
  session_id: string
  status: string
  current_agent: string | null
  progress: number
  total: number
  error: string | null
  report_id: string | null
  created_at: string | null
}

export async function uploadPDF(file: File): Promise<ApiResponse<UploadResult>> {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post<ApiResponse<UploadResult>>('/upload', form)
  return res.data
}

export async function getStatus(sessionId: string): Promise<ApiResponse<StatusResult>> {
  const res = await api.get<ApiResponse<StatusResult>>(`/status/${sessionId}`)
  return res.data
}
