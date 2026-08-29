# Agent 设计与伪代码

---

## 1. Milvus 知识库与混合检索

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
    limit=8, output_fields=["text", "page"]
)
```
- 切片策略：PyMuPDF 按页提取文本 → 按「标题层级/段落」切成 300–500 token 的 chunk，保留页码元数据
- 入库时附带 `session_id` 字段，检索时必须带 `expr=f'session_id == "{sid}"'` 隔离不同财报
- Embedding 模型：本地 `BAAI/bge-m3`（同时支持 dense+sparse）或 OpenAI 兼容 embedding API，配置化

---

## 2. 模型路由

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

## 3. ADK 多-Agent 流水线

### 3.1 编排（app/agents/pipeline/pipeline.py）
```python
from google.adk.agents import SequentialAgent
from app.agents.pipeline import pdf_parser, metric_extractor, risk_checker, report_writer

pipeline = SequentialAgent(
    name="financial_report_pipeline",
    sub_agents=[pdf_parser.agent, metric_extractor.agent,
                risk_checker.agent, report_writer.agent],
)
```

### 3.2 Agent 间数据传递
ADK `LlmAgent` 设 `output_key`，输出写入 `session.state`；下游 Agent 的 `instruction` 里用 `{pdf_chunks_summary}`、`{metrics_json}`、`{risk_findings}` 模板占位符自动注入上游结果。结构化大块数据（如指标 JSON）由工具直接写 MySQL/Milvus，Agent 间只传摘要 + 数据已持久化的确认，避免撑爆上下文。

### 3.3 四个 Agent 定义骨架
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

### 3.4 执行入口
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

### 3.5 多轮问答 Agent
独立 `LlmAgent(chat_agent)`：模型 GLM，挂载三类工具：
- `rag_search`（local_tools）：检索财报知识库
- `get_metrics_from_mysql`（local_tools）：查结构化指标
- `mcp_news_search`（mcp/news_client.py）：通过 MCP 协议连接 [financial-news-mcp-server](https://github.com/cdfnte/financial-news-mcp-server)，按公司名/股票代码拉取实时市场新闻，补充财报之外的即时信息

每次请求用独立 runner 运行，历史上下文从 Redis `chat` 列表拼装。

---

## 4. Function-Calling 工具

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
