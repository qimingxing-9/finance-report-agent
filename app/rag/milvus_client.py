# app/rag/milvus_client.py — Milvus 客户端封装
# - 建集合（BM25 sparse + bge-m3 dense 双索引）
# - 写入：向量化文本切片 → insert
# - 检索：hybrid_search（RRF 融合 BM25 + 向量结果）
# - 按 session_id 过滤隔离不同财报
