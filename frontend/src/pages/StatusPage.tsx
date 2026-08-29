import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getStatus, type StatusResult } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function StatusPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [data, setData] = useState<StatusResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function poll() {
      const res = await getStatus(sessionId!)
      if (!active) return
      if (res.code !== 0) {
        setError(res.msg)
        return
      }
      setData(res.data)
      if (res.data!.status === 'pending' || res.data!.status === 'running') {
        setTimeout(poll, 2000)
      }
    }

    poll()
    return () => { active = false }
  }, [sessionId])

  if (error) {
    return (
      <div className="text-center">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  if (!data) {
    return <p className="text-center text-gray-500">加载中...</p>
  }

  const agents = ['pdf_parser', 'metric_extractor', 'risk_checker', 'report_writer']
  const agentLabels: Record<string, string> = {
    pdf_parser: 'PDF 解析',
    metric_extractor: '指标提取',
    risk_checker: '风险校验',
    report_writer: '报告生成',
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h2 className="text-lg font-medium text-gray-800">任务状态</h2>
        <StatusBadge status={data.status} />
      </div>

      <div className="bg-white rounded-lg shadow-sm p-6 space-y-4">
        <div className="text-sm text-gray-500">Session ID</div>
        <div className="text-sm font-mono text-gray-700 break-all">{data.session_id}</div>

        <div className="border-t pt-4">
          <div className="text-sm text-gray-500 mb-3">流水线进度</div>
          <div className="space-y-2">
            {agents.map((agent, i) => {
              const done = data.progress > i
              const current = data.current_agent === agent
              return (
                <div key={agent} className="flex items-center gap-3">
                  <div className={`h-2 w-2 rounded-full ${done ? 'bg-green-500' : current ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'}`} />
                  <span className={`text-sm ${done || current ? 'text-gray-800' : 'text-gray-400'}`}>
                    {agentLabels[agent]}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {data.error && (
          <div className="border-t pt-4">
            <div className="text-sm text-red-600">错误: {data.error}</div>
          </div>
        )}
      </div>
    </div>
  )
}
