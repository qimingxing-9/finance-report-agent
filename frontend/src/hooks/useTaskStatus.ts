// src/hooks/useTaskStatus.ts — 轮询任务状态 hook
// - setInterval 轮询 GET /api/report/status/{sid}
// - 返回 { status, currentAgent, progress, reportId, error }
