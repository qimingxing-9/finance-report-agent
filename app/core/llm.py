# app/core/llm.py — 模型路由工厂
# - 用 ADK LiteLlm 包装 OpenAI 兼容端点
# - GLM：glm-5.3-flash，低成本，用于解析/提取/报告/问答
# - DEEPSEEK：deepseek-v4-pro，深度推理，用于风险校验
# - 闲时调度逻辑：判断当前时间是否在 OFF_PEAK_WINDOW 内
