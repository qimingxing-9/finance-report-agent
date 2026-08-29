# app/tools/local_tools/rag_tool.py — Milvus 混合检索工具
# - @tool rag_search(query, session_id, top_k)
# - 调用 app/rag/milvus_client.py 的 hybrid_search
# - BM25 + 向量混合召回，按 session_id 隔离
