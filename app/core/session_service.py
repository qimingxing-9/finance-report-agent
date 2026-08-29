# app/core/session_service.py — RedisSessionService
# - 继承 ADK BaseSessionService，扩展会话持久化至 Redis
# - 实现 create_session / get_session / append_event 等钩子
# - Key 设计：session:{sid}:status / events / state / chat
# - TTL 自动清理，支持中断恢复
