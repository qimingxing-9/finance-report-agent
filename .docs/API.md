# 接口文档

> Base URL: `http://localhost:8000`
> 统一响应信封：成功 `{ "code": 0, "data": {...} }`，失败 `{ "code": <非0>, "msg": "错误描述" }`

---

## 1. 上传财报 `POST /api/report/upload`

| 项目 | 内容 |
|---|---|
| Content-Type | `multipart/form-data` |
| 入参 | `file`：PDF 文件（≤20MB，校验 Content-Type 为 application/pdf） |
| 逻辑 | 保存至 `uploads/{session_id}.pdf` → 写 `report_info` 表 → Redis 初始化任务状态 → `asyncio.create_task` 启动流水线 |

**成功响应** `200`
```json
{
  "code": 0,
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "pending"
  }
}
```

**失败响应** `400`
```json
{ "code": 1001, "msg": "文件格式不支持，请上传 PDF" }
{ "code": 1002, "msg": "文件大小超过 20MB 限制" }
```

---

## 2. 查询任务状态 `GET /api/report/status/{session_id}`

**路径参数**：`session_id`（UUID）

**成功响应** `200`
```json
{
  "code": 0,
  "data": {
    "session_id": "550e8400-...",
    "status": "running",
    "current_agent": "risk_checker",     // 当前执行到的 Agent
    "progress": 3,                       // 已完成的 Agent 数（0-4）
    "total": 4,
    "error": null,                       // failed 时填错误信息
    "report_id": null,                   // success 时填报告 ID，供下载/查看
    "created_at": "2026-08-29T10:30:00Z"
  }
}
```

**status 枚举**

| status | 含义 | current_agent | report_id |
|---|---|---|---|
| `pending` | 排队中，流水线未启动 | null | null |
| `running` | 执行中 | 当前 Agent 名 | null |
| `success` | 全部完成 | null | 报告 ID（UUID） |
| `failed` | 异常终止 | 异常时所在 Agent | null |

**未找到** `404`
```json
{ "code": 2001, "msg": "session 不存在" }
```

---

## 3. 获取报告内容 `GET /api/report/{report_id}`

> 前端 `ReportViewer.tsx` 用此接口拿 Markdown 原文，用 `react-markdown` 渲染

**成功响应** `200`
```json
{
  "code": 0,
  "data": {
    "report_id": "r-abc123",
    "session_id": "550e8400-...",
    "title": "XX公司2025年度财报分析报告",
    "content_md": "# 公司概况\n\n...",
    "created_at": "2026-08-29T10:35:00Z"
  }
}
```

**未找到** `404`
```json
{ "code": 2002, "msg": "报告不存在" }
```

---

## 4. 下载报告文件 `GET /api/report/download/{report_id}`

**成功响应** `200` — 直接返回文件流
- Content-Type: `text/markdown`
- Content-Disposition: `attachment; filename="report.md"`

**未找到** `404` — 同第 3 节

---

## 5. 多轮问答 `POST /api/report/chat`

**请求体**
```json
{
  "session_id": "550e8400-...",
  "question": "本年度毛利率变化的原因是什么？"
}
```

**前置校验**：任务状态必须为 `success`，否则返回 `400`
```json
{ "code": 3001, "msg": "报告尚未生成完成，请稍后再试" }
```

**成功响应** `200`
```json
{
  "code": 0,
  "data": {
    "session_id": "550e8400-...",
    "answer": "本年度毛利率从 32.1% 下降至 28.5%，主要原因是原材料成本上升……",
    "turn": 3,                          // 当前对话轮次
    "sources": [                         // 引用来源（RAG 检索命中的切片）
      { "page": 12, "text": "营业成本同比增长 18.3%……" },
      { "page": 27, "text": "主要原材料采购均价上涨 22%……" }
    ]
  }
}
```

**未找到** `404` — 同第 2 节

---

## 6. 错误码汇总

| code | 含义 |
|---|---|
| 0 | 成功 |
| 1001 | 文件格式不支持 |
| 1002 | 文件大小超限 |
| 2001 | session 不存在 |
| 2002 | 报告不存在 |
| 3001 | 报告尚未生成完成 |
| 3002 | 问答内容为空 |
| 5000 | 服务内部错误 |
