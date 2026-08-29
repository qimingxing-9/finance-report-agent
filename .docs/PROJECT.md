# 金融财报多-Agent 智能分析平台 · 项目说明书

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
├── .docs/                     # 项目文档目录
│   ├── PROJECT.md             # 项目说明书（本文档）
│   ├── API.md                 # 接口文档
│   ├── DATABASE.md            # 数据库文档（MySQL + Redis）
│   └── AGENT_DESIGN.md        # Agent 设计与伪代码（流水线 / Milvus / 工具）
├── app/
│   ├── main.py                 # FastAPI 入口、生命周期管理
│   ├── config.py               # pydantic-settings 环境配置
│   ├── api/
│   │   └── report.py           # 5 个 REST 接口
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

### 文档索引

| 文档 | 内容 |
|---|---|
| [API.md](./API.md) | 5 个 REST 接口定义、请求/响应格式、错误码汇总 |
| [DATABASE.md](./DATABASE.md) | MySQL 三张表 DDL、Redis Key 设计与持久化策略 |
| [AGENT_DESIGN.md](./AGENT_DESIGN.md) | Milvus 混合检索、模型路由、ADK 流水线编排、Function-Calling 工具伪代码 |

---

## 3. 核心业务流程（时序）

1. `upload`：生成 `session_id` → PDF 落盘 → `report_info` 入库 → Redis 状态 `pending` → `asyncio.create_task` 启动流水线，状态置 `running`
2. **PDF解析Agent**：`extract_and_chunk_pdf` 工具读 PDF → 切片（含页码）→ bge-m3 向量化 → 写 Milvus（先删后插保证幂等）→ 回写 `company_name/report_year`
3. **指标提取Agent**：`rag_search` 召回各指标相关切片 → LLM 结构化抽取 → 逐条写 `financial_metric` 表
4. **风险校验Agent**（DeepSeek）：读指标 → 调用计算工具算同比/环比/比率 → 勾稽校验 → 风险点结论写入 state；非闲时段则等待闲时窗口再执行
5. **报告生成Agent**：汇总 state 中三阶段产出 → 生成 Markdown → 写 `analysis_report` + 落盘 `reports/`
6. 全程事件 rpush 至 Redis `events`；完成后状态 `success`，异常则 `failed` 并记录 error
7. `status` 轮询 → `download` 取报告 → `chat` 基于 RAG + 会话历史多轮问答

---

## 4. 部署

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

## 5. 开发里程碑

| 阶段 | 内容 | 验收标准 |
|---|---|---|
| 1 | FastAPI 骨架 + 上传/状态接口 + MySQL 三表 | curl 上传后 status 可轮询 |
| 2 | Redis 任务状态 + asyncio 后台任务 + 状态机 | 状态流转 pending→running→success/failed |
| 3 | PDF 切片 + Milvus 入库 + 混合检索独立跑通 | rag_search 返回相关切片 |
| 4 | ADK 单 Agent（pdf_parser）最小 Demo | Runner 事件正常产生 |
| 5 | 财务工具 + 四 Agent 拆分 + SequentialAgent 流水线 | 上传 PDF 端到端产出报告 |
| 6 | 模型路由 + DeepSeek 闲时调度 | 风险校验走 DeepSeek |
| 7 | chat 多轮问答 + Redis 会话恢复 + MCP 新闻接入 | 重启服务后问答仍有上下文 |
| 8 | Docker-Compose 整体联调 + 中断恢复测试 | `docker compose up` 一键可用 |

---

## 6. 面试亮点速记

1. **SequentialAgent 流水线**：任务解耦、Agent 职责单一，`output_key` + state 模板实现 Agent 间通信
2. **分层记忆**：自定义 `RedisSessionService` 扩展 ADK 会话持久化（事件/状态/对话三结构 + TTL + 中断恢复）；Milvus 作长期知识库
3. **BM25 + 向量混合检索**（Milvus 内置 BM25 Function + RRF 融合），按 session 分区隔离，显著降低长财报问答幻觉
4. **模型动态路由**：Flash 干粗活、Pro 干推理，闲时窗口调度降 API 成本
5. **Function-Calling**：一切财务计算由确定性代码执行，工具内做除零等边界防护，LLM 只编排不算数
6. **MCP 外部工具集成**：通过 MCP 协议连接新闻服务，chat_agent 动态编排工具调用（不走固定 workflow）
