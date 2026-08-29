# 金融财报多-Agent 智能分析平台

> 基于 Google-ADK 多 Agent 协同架构的上市公司财报智能分析后端

上传财报 PDF → 自动完成 **PDF 解析 → 财务指标提取 → 风险校验 → 报告生成** 全流程，输出 Markdown 分析报告，并支持基于报告内容的多轮问答。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + Uvicorn |
| Agent 编排 | Google ADK（SequentialAgent 串行流水线） |
| 大模型 | GLM-5.3-Flash / DeepSeek-V4-Pro（LiteLlm 包装，动态路由） |
| 短期记忆 | Redis（自定义 RedisSessionService 扩展 ADK 会话持久化） |
| 长期知识库 | Milvus 2.4+（BM25 + 向量混合检索，bge-m3 embedding） |
| 数据库 | MySQL 8.0 + SQLAlchemy async |
| PDF 解析 | PyMuPDF |
| 前端 | React + Vite + TailwindCSS |
| 部署 | Docker Compose |

## 核心特性

- **SequentialAgent 流水线**：4 个 Agent 职责单一，`output_key` + state 模板实现 Agent 间通信
- **分层记忆架构**：Redis 持久化会话事件（短期，支持中断恢复）；Milvus 财报知识库（长期）
- **BM25 + 向量混合检索**：Milvus 内置 BM25 Function + RRF 融合，按 session 分区隔离，降低长财报幻觉
- **模型动态路由**：简单任务走 Flash，深度推理走 Pro，闲时窗口调度降成本
- **Function-Calling 财务工具**：同比/环比/毛利率/资产负债率计算由确定性代码执行，禁止 LLM 算数
- **MCP 外部工具集成**：通过 MCP 协议接入新闻服务，多轮问答 Agent 动态编排工具调用

## 项目结构

```
finance_agent/
├── app/
│   ├── api/           # REST 接口（上传/状态/报告/问答）
│   ├── agents/        # ADK Agent（pipeline 流水线 + chat 独立问答）
│   ├── tools/         # local_tools + mcp + skills
│   ├── core/          # 模型路由 / Redis 会话 / 任务管理
│   ├── rag/           # Milvus 客户端 / Embedding
│   ├── storage/       # MySQL / Redis 连接 + ORM
│   └── schemas/       # Pydantic 请求/响应模型
├── frontend/          # React + Vite + TailwindCSS
├── .docs/             # 项目文档（API / 数据库 / Agent 设计）
├── sql/               # MySQL 建表脚本
└── docker-compose.yml
```

## 快速启动

```bash
# 后端
pip install -r requirements.txt
cp .env.example .env  # 填入 API Key 和数据库连接
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev
```

## 开发进度

- [x] 阶段一：FastAPI 骨架 + 上传/状态接口 + MySQL 三表 + 前端上传/状态页
- [ ] 阶段二：Redis 任务状态 + asyncio 后台任务 + 状态机
- [ ] 阶段三：PDF 切片 + Milvus 入库 + 混合检索
- [ ] 阶段四：ADK 单 Agent 最小 Demo
- [ ] 阶段五：四 Agent + SequentialAgent 流水线
- [ ] 阶段六：模型路由 + DeepSeek 闲时调度
- [ ] 阶段七：多轮问答 + MCP 新闻接入
- [ ] 阶段八：Docker-Compose 整体联调
