# app/tools/local_tools/pdf_tool.py — PDF 读取与切片工具
# - PyMuPDF 按页提取文本 → 按标题/段落切成 300-500 token chunk
# - 保留页码元数据 → bge-m3 向量化 → 写 Milvus（先删后插，幂等）
# - ADK @tool 装饰器，供 pdf_parser Agent 调用
