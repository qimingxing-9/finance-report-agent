# 金融财报多-Agent 智能分析平台 · 开发文档

> 技术栈：FastAPI + Google-ADK + Redis + Milvus + MySQL + Docker
> 架构形态：单服务单体，接口层与 Agent 工作流同进程运行

---

## 1. 项目简介

面向上市公司财报 PDF 的智能分析后端：上传 PDF 后自动完成 **解析 → 指标提取 → 风险校验 → 报告生成** 的多-Agent 流水线，输出 Markdown 财务分析报告，并支持基于报告内容的多轮问答。

- **多-Agent 编排**：Google-ADK `SequentialAgent` 串行流水线，4 个 Agent 职责单一
- **分层记忆**：Redis 持久化 ADK 会话事件（短期）；Milvus 财报切片知识库（长期）
- **混合检索**：BM25 + 向量混合召回，降低长文档场景下的幻觉
- **模型路由**：简单任务走 GLM-5.3-Flash，深度推理任务走 DeepSeek-V4-Pro，控制成本
- **Function-Calling**：财务计算封装为工具函数，禁止大模型自行算数

---

## 2. 目录结构

```
finance_agent/
├── app/
│   ├── main.py                 # FastAPI 入口、生命周期管理
│   ├── config.py               # pydantic-settings 环境配置
│   ├── api/
│   │   └── report.py           # 4 个 REST 接口
│   ├── core/
│   │   ├── llm.py              # 模型路由工厂（GLM / DeepSeek）
│   │   ├── session_service.py  # RedisSessionService：ADK 会话持久化扩展
│   │   └── task_manager.py     # asyncio 后台任务 + 状态机
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── pipeline/               # 固定流水线（workflow）
│   │   │   ├── __init__.py
│   │   │   ├── pipeline.py         # SequentialAgent 编排入口
│   │   │   ├── pdf_parser.py       # PDF解析Agent
│   │   │   ├── metric_extractor.py # 指标提取Agent
│   │   │   ├── risk_checker.py     # 风险校验Agent（DeepSeek）
│   │   │   └── report_writer.py    # 报告生成Agent
│   │   └── chat/                   # 独立问答Agent（动态编排，不走 workflow）
│   │       ├── __init__.py
│   │       └── chat_agent.py       # 多轮问答Agent（独立Runner）
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── local_tools/            # 本地实现的工具
│   │   │   ├── __init__.py
│   │   │   ├── pdf_tool.py         # PDF 读取 / 切片
│   │   │   ├── finance_tools.py    # 同比/环比/毛利率/资产负债率
│   │   │   └── rag_tool.py         # Milvus 混合检索工具
│   │   ├── mcp/                    # 外部 MCP 工具客户端
│   │   │   ├── __init__.py
│   │   │   └── news_client.py     # 连接 financial-news-mcp-server，获取公司/市场新闻
│   │   │                           # 职责：①建立与 MCP server 连接 ②能力发现(tools/resources/prompts) ③发请求收结果
│   │   └── skills/                 # 技能定义
│   │       └── __init__.py         # 复合技能放此目录
│   ├── rag/
│   │   ├── milvus_client.py    # 建表、写入、混合检索封装
│   │   └── embedding.py        # Embedding 客户端
│   ├── storage/
│   │   ├── redis_client.py     # Redis 连接与 Key 封装
│   │   ├── mysql.py            # SQLAlchemy async engine/session
│   │   └── models.py           # ORM 三张表
│   └── schemas/
│       └── api.py              # Pydantic 请求/响应模型
├── sql/init.sql                # MySQL 建表脚本
├── uploads/                    # PDF 落盘目录（挂载卷）
├── reports/                    # Markdown 报告目录（挂载卷）
├── frontend/                   # React 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx            # 应用入口
│       ├── App.tsx             # 路由定义（React Router）
│       ├── api/
│       │   └── client.ts       # 后端 API 封装（upload/status/chat/download）
│       ├── components/
│       │   ├── FileUpload.tsx   # PDF 上传组件（拖拽 + 进度条）
│       │   ├── StatusBadge.tsx   # 任务状态徽标（pending/running/success/failed）
│       │   ├── ChatWindow.tsx    # 多轮问答对话框（流式渲染）
│       │   └── ReportViewer.tsx  # Markdown 报告渲染（react-markdown）
│       ├── pages/
│       │   ├── UploadPage.tsx     # 上传页：上传 PDF → 跳转状态页
│       │   ├── StatusPage.tsx     # 状态页：轮询任务状态 → 完成后跳报告页
│       │   ├── ReportPage.tsx     # 报告页：查看/下载 Markdown 报告
│       │   └── ChatPage.tsx       # 问答页：基于已生成报告多轮问答
│       └── hooks/
│           ├── useTaskStatus.ts   # 轮询任务状态 hook
│           └── useChat.ts         # 多轮问答状态管理 hook
├── docker-compose.yml          # 含 app + mysql + redis + milvus + frontend
├── Dockerfile                  # 后端镜像
├── frontend.Dockerfile         # 前端镜像（Vite build → nginx 托管）
├── requirements.txt
└── .env
```

---

## 3. 接口定义

> Base URL: `http://localhost:8000`
> 统一响应信封：成功 `{ "code": 0, "data": {...} }`，失败 `{ "code": <非0>, "msg": "错误描述" }`

### 3.1 上传财报 `POST /api/report/upload`

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

### 3.2 查询任务状态 `GET /api/report/status/{session_id}`

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

### 3.3 获取报告内容 `GET /api/report/{report_id}`

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

### 3.4 下载报告文件 `GET /api/report/download/{report_id}`

**成功响应** `200` — 直接返回文件流
- Content-Type: `text/markdown`
- Content-Disposition: `attachment; filename="report.md"`

**未找到** `404` — 同 3.3

---

### 3.5 多轮问答 `POST /api/report/chat`

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

**未找到** `404` — 同 3.2

---

### 3.6 错误码汇总

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

---

## 4. MySQL 表设计（sql/init.sql）

```sql
CREATE TABLE report_info (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id    VARCHAR(64)  NOT NULL UNIQUE,
    file_name     VARCHAR(255) NOT NULL,
    file_path     VARCHAR(512) NOT NULL,
    company_name  VARCHAR(128) DEFAULT NULL,     -- 解析阶段回填
    report_year   INT          DEFAULT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE financial_metric (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    session_id    VARCHAR(64) NOT NULL,
    metric_name   VARCHAR(64)  NOT NULL,   -- 净利润/营业收入/毛利率/资产负债率/经营现金流...
    metric_value  DECIMAL(18,4) DEFAULT NULL,
    period        VARCHAR(32)  NOT NULL,   -- 如 2024FY / 2025H1 / 2025Q3
    yoy           DECIMAL(10,4) DEFAULT NULL,  -- 同比，由风险校验Agent回填
    qoq           DECIMAL(10,4) DEFAULT NULL,  -- 环比
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session_period (session_id, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE analysis_report (
    id            BIGINT PRIMARY KEY AUTO_INCREMENT,
    report_id     VARCHAR(64) NOT NULL UNIQUE,   -- 对外暴露的下载 ID
    session_id    VARCHAR(64) NOT NULL,
    title         VARCHAR(255) NOT NULL,
    content_md    LONGTEXT     NOT NULL,          -- Markdown 全文
    file_path     VARCHAR(512) NOT NULL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 5. Redis 会话持久化设计（核心扩展点）

ADK 原生 `InMemorySessionService` 重启即丢；自定义 `RedisSessionService` 继承 `BaseSessionService`，在 `create_session / get_session / append_event` 等钩子里同步读写 Redis。

### Key 设计
| Key | 类型 | 内容 | TTL |
|---|---|---|---|
| `session:{sid}:status` | String | pending/running/success/failed + error | 7 天 |
| `session:{sid}:events` | List | ADK 事件 JSONL（逐条 rpush，可截断保留最近 N=200 条） | 7 天 |
| `session:{sid}:state` | Hash | Agent 间传递的状态快照（parser→metric→risk→report 各阶段产出摘要） | 7 天 |
| `session:{sid}:chat` | List | 多轮问答 [{role, content}]（保留最近 20 轮） | 7 天 |

### 中断恢复
服务启动时扫描所有 `status=running` 的 session：重新执行流水线（PDF 已落盘，Milvus 切片按 `session_id` 分区先删后插，保证幂等）。

### 多轮问答
chat 接口先从 `session:{sid}:chat` 读取历史拼入 prompt（或恢复 ADK Session），回答完成后 rpush 追加，防止上下文无限膨胀。

---

## 6. Milvus 知识库与混合检索

### Collection Schema（每 session 一个分区，`partition_key` 或按 expr 过滤）
```python
# milvus 2.4+，BM25 稀疏检索用内置 Function 生成，无需自建 ES
fields:
    id          INT64, auto_id, primary key
    text        VARCHAR(2048)
    sparse      SPARSE_FLOAT_VECTOR   # 由 BM25 Function 从 text 自动生成
    dense       FLOAT_VECTOR(1024)    # bge-m3 dense embedding
functions:
    bm25 = Function(type=BM25, input_field_names=["text"],
                    output_field_names=["sparse"])
index:
    dense  -> HNSW / COSINE
    sparse -> SPARSE_INVERTED_INDEX / BM25
```

### 混合检索
```python
res = collection.hybrid_search(
    reqs=[sparse_req, dense_req],          # 同一 query 两路召回
    ranker=RRFRanker(k=60),                # 或 WeightedRanker(0.3, 0.7)
    limit=8, output_fields=["text", "page"])
```
- 切片策略：PyMuPDF 按页提取文本 → 按「标题层级/段落」切成 300–500 token 的 chunk，保留页码元数据
- 入库时附带 `session_id` 字段，检索时必须带 `expr=f'session_id == "{sid}"'` 隔离不同财报
- Embedding 模型：本地 `BAAI/bge-m3`（同时支持 dense+sparse）或 OpenAI 兼容 embedding API，配置化

---

## 7. 模型路由

`app/core/llm.py` 统一用 ADK 的 `LiteLlm` 包装 OpenAI 兼容端点：

```python
from google.adk.models.lite_llm import LiteLlm

GLM = LiteLlm(model="openai/glm-5.3-flash",
              api_base="https://open.bigmodel.cn/api/paas/v4",
              api_key=SETTINGS.glm_api_key)

DEEPSEEK = LiteLlm(model="openai/deepseek-v4-pro",
                   api_base="https://api.deepseek.com/v1",
                   api_key=SETTINGS.deepseek_api_key)
```

| Agent | 模型 | 原因 |
|---|---|---|
| PDF解析 / 指标提取 / 报告生成 / 问答 | GLM-5.3-Flash | 大 token 消耗的机械性任务，低成本 |
| 风险校验 | DeepSeek-V4-Pro | 勾稽校验需强推理能力；闲时段（如 00:30–08:30）直接同步调用，费用减半——若上传发生在闲时外，任务保持 running 至闲时窗口再启动该 Agent |

---

## 8. ADK 多-Agent 流水线

### 8.1 编排（app/agents/pipeline/pipeline.py）
```python
from google.adk.agents import SequentialAgent
from app.agents.pipeline import pdf_parser, metric_extractor, risk_checker, report_writer

pipeline = SequentialAgent(
    name="financial_report_pipeline",
    sub_agents=[pdf_parser.agent, metric_extractor.agent,
                risk_checker.agent, report_writer.agent],
)
```

### 8.2 Agent 间数据传递
ADK `LlmAgent` 设 `output_key`，输出写入 `session.state`；下游 Agent 的 `instruction` 里用 `{pdf_chunks_summary}`、`{metrics_json}`、`{risk_findings}` 模板占位符自动注入上游结果。结构化大块数据（如指标 JSON）由工具直接写 MySQL/Milvus，Agent 间只传摘要 + 数据已持久化的确认，避免撑爆上下文。

### 8.3 四个 Agent 定义骨架
```python
# app/agents/pipeline/pdf_parser.py
from google.adk.agents import LlmAgent
from app.tools.local_tools.pdf_tool import extract_and_chunk_pdf
from app.core.llm import GLM

agent = LlmAgent(
    name="pdf_parser",
    model=GLM,
    tools=[extract_and_chunk_pdf],        # 工具内部完成：读PDF→切片→写Milvus
    output_key="pdf_chunks_summary",
    instruction="调用 extract_and_chunk_pdf 解析上传的财报PDF，"
                "返回切片数量与文档结构概览。不要复述原文。",
)
```
```python
# app/agents/pipeline/risk_checker.py —— 深度推理 + 闲时调度
agent = LlmAgent(
    name="risk_checker",
    model=DEEPSEEK,
    tools=[calc_yoy, calc_qoq, calc_gross_margin, calc_debt_ratio,
           get_metrics_from_mysql],
    output_key="risk_findings",
    instruction="从 {metrics_json} 读取各期财务指标。"
                "必须调用财务计算工具完成同比/环比/毛利率/资产负债率计算，禁止心算。"
                "校验勾稽关系：净利润≈营业收入×(1-成本费用率区间)、"
                "经营现金流与净利润背离、资产负债率>70%等，输出风险点列表。",
)
```
```python
# app/agents/pipeline/report_writer.py
agent = LlmAgent(
    name="report_writer",
    model=GLM,
    output_key="final_report_md",
    instruction="基于 {pdf_chunks_summary}、{metrics_json}、{risk_findings}，"
                "生成完整Markdown财报分析报告，章节：公司概况/经营业绩/财务指标分析/"
                "风险提示/结论。",
)
```

### 8.4 执行入口
```python
runner = Runner(agent=pipeline, app_name="finance_agent",
                session_service=redis_session_service)

async def run_pipeline(session_id: str):
    content = types.Content(role="user",
                parts=[types.Part(text=f"分析财报 {session_id}")])
    async for event in runner.run_async(user_id=session_id,
                                        session_id=session_id, content=content):
        await redis_session_service.persist_event(session_id, event)  # 事件落Redis
    # 流水线结束后：报告Agent的 output_key 已在 state 中，落MySQL并更新状态
```

### 8.5 多轮问答 Agent
独立 `LlmAgent(chat_agent)`：模型 GLM，挂载三类工具：
- `rag_search`（local_tools）：检索财报知识库
- `get_metrics_from_mysql`（local_tools）：查结构化指标
- `mcp_news_search`（mcp/news_client.py）：通过 MCP 协议连接 [financial-news-mcp-server](https://github.com/cdfnte/financial-news-mcp-server)，按公司名/股票代码拉取实时市场新闻，补充财报之外的即时信息

每次请求用独立 runner 运行，历史上下文从 Redis `chat` 列表拼装。

---

## 9. Function-Calling 工具

```python
# app/tools/local_tools/finance_tools.py —— 计算逻辑全部程序化，LLM 只负责调用
from google.adk.tools import tool

@tool
def calc_yoy(current: float, previous: float) -> dict:
    """计算同比增长率(%)。current: 本期值; previous: 上年同期值。"""
    if previous == 0:
        return {"error": "基期为0，无法计算同比"}
    return {"yoy": round((current - previous) / abs(previous) * 100, 4)}

@tool
def calc_gross_margin(revenue: float, cost: float) -> dict:
    """计算毛利率(%)。revenue: 营业收入; cost: 营业成本。"""
    if revenue == 0:
        return {"error": "营业收入为0"}
    return {"gross_margin": round((revenue - cost) / revenue * 100, 4)}

@tool
def calc_debt_ratio(total_liability: float, total_asset: float) -> dict: ...
@tool
def calc_qoq(current: float, previous: float) -> dict: ...   # 同calc_yoy口径
@tool
def get_metrics_from_mysql(session_id: str) -> list[dict]: ...  # SQLAlchemy查询
```

```python
# app/tools/local_tools/rag_tool.py
@tool
def rag_search(query: str, session_id: str, top_k: int = 8) -> list[dict]:
    """BM25+向量混合检索财报知识库，返回相关切片及页码。"""
    return milvus_client.hybrid_search(session_id, query, top_k)
```

```python
# app/tools/mcp/news_client.py —— MCP 外部工具客户端
#
# 每个 mcp/ 下的 client 统一承担三项职责：
# 1. 建立连接：与 MCP server 建立 stdio/SSE 连接，管理生命周期（连接/断线重连/关闭）
# 2. 能力发现：连接后调用 list_tools / list_resources / list_prompts，获取 server 暴露的能力清单
# 3. 请求与响应：Agent 运行时通过 client 调用 server 的 tool（call_tool）或读取 resource（read_resource），发送请求并接收结构化结果
#
# --- news_client 具体配置 ---
# 连接的 MCP server: financial-news-mcp-server（https://github.com/cdfnte/financial-news-mcp-server）
# 数据源：Yahoo Finance（实时市场新闻）/ NewsAPI（公司个股新闻）/ Contalion（热点）
# Agent 通过 mcp_news_search 工具按公司名或股票代码获取相关新闻
# 集成方式：ADK MCP client 连接外部 MCP server stdio/SSE 端点，工具自动注入 Agent
# 待开发：安装 financial-news-mcp-server → 配置 MCP 端点 → 注册到 chat_agent
```

---

## 10. 核心业务流程（时序）

1. `upload`：生成 `session_id` → PDF 落盘 → `report_info` 入库 → Redis 状态 `pending` → `asyncio.create_task` 启动流水线，状态置 `running`
2. **PDF解析Agent**：`extract_and_chunk_pdf` 工具读 PDF → 切片（含页码）→ bge-m3 向量化 → 写 Milvus（先删后插保证幂等）→ 回写 `company_name/report_year`
3. **指标提取Agent**：`rag_search` 召回各指标相关切片 → LLM 结构化抽取 → 逐条写 `financial_metric` 表
4. **风险校验Agent**（DeepSeek）：读指标 → 调用计算工具算同比/环比/比率 → 勾稽校验 → 风险点结论写入 state；非闲时段则等待闲时窗口再执行
5. **报告生成Agent**：汇总 state 中三阶段产出 → 生成 Markdown → 写 `analysis_report` + 落盘 `reports/`
6. 全程事件 rpush 至 Redis `events`；完成后状态 `success`，异常则 `failed` 并记录 error
7. `status` 轮询 → `download` 取报告 → `chat` 基于 RAG + 会话历史多轮问答

---

## 11. 部署

### docker-compose.yml
```yaml
services:
  app:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    volumes:
      - ./uploads:/app/uploads
      - ./reports:/app/reports
    depends_on:
      mysql:    { condition: service_healthy }
      redis:    { condition: service_started }
      milvus:   { condition: service_started }
  frontend:
    build:
      context: ./frontend
      dockerfile: ../frontend.Dockerfile
    ports: ["3000:80"]               # nginx 托管 Vite 构建产物
    depends_on: [app]
  mysql:
    image: mysql:8.0
    environment: { MYSQL_ROOT_PASSWORD: root123, MYSQL_DATABASE: finance }
    volumes: ["./sql/init.sql:/docker-entrypoint-initdb.d/init.sql", "mysql_data:/var/lib/mysql"]
    healthcheck: { test: ["CMD", "mysqladmin", "ping", "-h", "localhost"], interval: 5s, retries: 10 }
  redis:
    image: redis:7-alpine
    volumes: ["redis_data:/data"]
  etcd:
    image: quay.io/coreos/etcd:v3.5.14
    environment: [ALLOW_NONE_AUTHENTICATION=yes]
  milvus:
    image: milvusdb/milvus:v2.4.17
    command: ["milvus", "run", "standalone"]
    depends_on: [etcd]
    ports: ["19530:19530"]
    volumes: ["milvus_data:/var/lib/milvus"]
volumes: { mysql_data: {}, redis_data: {}, milvus_data: {} }
```

### .env
```
GLM_API_KEY=xxx
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4
DEEPSEEK_API_KEY=xxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
EMBEDDING_MODEL=BAAI/bge-m3
MYSQL_URL=mysql+aiomysql://root:root123@mysql:3306/finance
REDIS_URL=redis://redis:6379/0
MILVUS_URI=http://milvus:19530
SESSION_TTL_DAYS=7
OFF_PEAK_WINDOW=00:30-08:30
```

### requirements.txt
```
fastapi uvicorn[standard] pydantic-settings
google-adk litellm
pymupdf
pymilvus[model]          # 含 bge-m3 本地 embedding 依赖
sqlalchemy[asyncio] aiomysql
redis
python-multipart
```

---

## 12. 开发里程碑

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| 1 | FastAPI 骨架 + 上传/状态接口 + MySQL 三表 | curl 上传后 status 可轮询 |
| 2 | Redis 任务状态 + asyncio 后台任务 + 状态机 | 状态流转 pending→running→success/failed |
| 3 | PDF 切片 + Milvus 入库 + 混合检索独立跑通 | rag_search 返回相关切片 |
| 4 | ADK 单 Agent（pdf_parser）最小 Demo | Runner 事件正常产生 |
| 5 | 财务工具 + 四 Agent 拆分 + SequentialAgent 流水线 | 上传 PDF 端到端产出报告 |
| 6 | 模型路由 + DeepSeek 闲时调度 | 风险校验走 DeepSeek |
| 7 | chat 多轮问答 + Redis 会话恢复 | 重启服务后问答仍有上下文 |
| 8 | Docker-Compose 整体联调 + 中断恢复测试 | `docker compose up` 一键可用 |

---

## 13. 面试亮点速记

1. **SequentialAgent 流水线**：任务解耦、Agent 职责单一，`output_key` + state 模板实现 Agent 间通信
2. **分层记忆**：自定义 `RedisSessionService` 扩展 ADK 会话持久化（事件/状态/对话三结构 + TTL + 中断恢复）；Milvus 作长期知识库
3. **BM25 + 向量混合检索**（Milvus 内置 BM25 Function + RRF 融合），按 session 分区隔离，显著降低长财报问答幻觉
4. **模型动态路由**：Flash 干粗活、Pro 干推理，闲时窗口调度降 API 成本
5. **Function-Calling**：一切财务计算由确定性代码执行，工具内做除零等边界防护，LLM 只编排不算数
