interface StatusBadgeProps {
  status: string
}

const config: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700',
  running: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
}

const labels: Record<string, string> = {
  pending: '等待中',
  running: '执行中',
  success: '已完成',
  failed: '失败',
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const cls = config[status] || 'bg-gray-100 text-gray-700'
  const label = labels[status] || status
  return (
    <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${cls}`}>
      {label}
    </span>
  )
}
