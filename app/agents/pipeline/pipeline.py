# app/agents/pipeline/pipeline.py — SequentialAgent 编排入口
# - 将 4 个 Agent 串行编排：pdf_parser → metric_extractor → risk_checker → report_writer
# - 上一 Agent 的 output_key 写入 session.state，下一 Agent 通过模板占位符读取
