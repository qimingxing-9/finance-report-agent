# AGENTS.md

> 本文件指导 AI Agent 在本项目中如何工作。开发前必读。

---

## 1. 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn |
| Agent 编排 | Google ADK（SequentialAgent / LlmAgent） |
| 大模型 | GLM-5.3-Flash（轻量任务）、DeepSeek-V4-Pro（深度推理），LiteLlm 包装 |
| 短期记忆 | Redis（ADK 会话持久化扩展） |
| 长期知识库 | Milvus 2.4+（BM25 + 向量混合检索，bge-m3 embedding） |
| 业务数据库 | MySQL 8.0 + SQLAlchemy async |
| PDF 解析 | PyMuPDF |
| 前端 | React + Vite + TailwindCSS + React Router |
| 部署 | Docker Compose（app + frontend + mysql + redis + milvus + etcd） |

---

## 2. 目录与文档约定

### 目录
- `app/` — 后端代码，Python 包
- `frontend/` — React 前端，独立构建
- `.docs/` — 所有项目文档（.md 文件）
- `sql/` — MySQL 建表脚本
- `uploads/` `reports/` — 运行时数据目录（已 gitignore）

### 文档
- `.docs/PROJECT.md` — 项目说明书，总览入口
- `.docs/API.md` — 接口文档
- `.docs/DATABASE.md` — 数据库文档
- `.docs/AGENT_DESIGN.md` — Agent 设计与伪代码
- 改了哪个模块，同步更新对应文档，不要只改代码不更新文档

### 代码约定
- Python 异步优先：`async def`，数据库用 `aiomysql`、Redis 用 `redis.asyncio`
- Agent 间不直接传大数据，结构化数据写 MySQL/Milvus，Agent 间只传摘要
- 新增工具放 `app/tools/local_tools/`，新增 MCP 客户端放 `app/tools/mcp/`
- 前端 API 调用统一走 `frontend/src/api/client.ts`

---

## 3. 禁止清单

1. **禁止**在代码中硬编码 API Key、数据库密码等敏感信息，一律走 `.env` + `config.py`
2. **禁止**让 LLM 自行计算财务数据，所有计算必须走 Function-Calling 工具
3. **禁止**在 `main` 分支上直接开发新功能，复杂功能开分支
4. **禁止**提交 `.env`、`uploads/`、`reports/`、`node_modules/` 等运行时文件
5. **禁止**使用 `print()` 调试，用 `logging` 模块
6. **禁止**同步阻塞调用在 async 路由中（如 `time.sleep`、同步 HTTP 请求）
7. **禁止**跨 Agent 直接引用对方内部实现，Agent 间只通过 `session.state` 的 `output_key` 通信
8. **禁止**跳过 `.docs/` 文档更新直接提交代码

---

## 4. 工作流程

### Git
- 主分支：`main`，保持可运行状态
- 开发分支命名：`feat/模块名`（如 `feat/fastapi-skeleton`）、`fix/问题描述`
- 提交信息格式：`type: 描述`（type ∈ init/feat/fix/refactor/docs/test）
- 提交后由用户决定是否 push，不自动推送

### 开发顺序
按 PROJECT.md 第 5 节里程碑顺序推进，每个阶段验收通过再进入下一阶段。

### 修改流程
1. 先读 `.docs/` 中相关文档，理解设计意图
2. 改代码 + 同步更新对应 `.docs/` 文档
3. 提交时代码和文档放在同一个 commit
4. 告知用户改了什么、为什么改

---

## 5. 关键设计决策（勿擅自变更）

- **单体服务**：不拆微服务，接口层与 Agent 同进程
- **SequentialAgent**：4 个 Agent 固定顺序，不走动态编排
- **chat_agent 独立**：不在 pipeline 内，用自己的 Runner，动态编排工具调用
- **模型路由**：Flash 干粗活，Pro 干推理，闲时调度降成本
- **Redis 会话持久化**：自定义 `RedisSessionService` 扩展 ADK，非原生内存方案
