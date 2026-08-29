# app/agents/chat/chat_agent.py — 多轮问答 Agent（独立 Runner）
# - 模型：GLM-5.3-Flash
# - 工具：rag_search + get_metrics_from_mysql + mcp_news_search
# - 不在 SequentialAgent 内，独立 Runner 执行
# - 历史上下文从 Redis chat 列表拼装
