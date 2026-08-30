import json

import redis.asyncio as redis_async

from app.config import settings

redis = redis_async.from_url(settings.redis_url, decode_responses=True)

SESSION_TTL = settings.session_ttl_days * 86400  # 秒


def _key_status(sid: str) -> str:
    return f"session:{sid}:status"


def _key_events(sid: str) -> str:
    return f"session:{sid}:events"


def _key_state(sid: str) -> str:
    return f"session:{sid}:state"


def _key_chat(sid: str) -> str:
    return f"session:{sid}:chat"


async def set_task_status(
    sid: str,
    status: str,
    current_agent: str | None = None,
    progress: int = 0,
    total: int = 4,
    error: str | None = None,
    report_id: str | None = None,
    created_at: str | None = None,
):
    data = {
        "session_id": sid,
        "status": status,
        "current_agent": current_agent,
        "progress": progress,
        "total": total,
        "error": error,
        "report_id": report_id,
        "created_at": created_at,
    }
    await redis.set(_key_status(sid), json.dumps(data, ensure_ascii=False), ex=SESSION_TTL)


async def get_task_status(sid: str) -> dict | None:
    raw = await redis.get(_key_status(sid))
    if raw is None:
        return None
    return json.loads(raw)


async def update_task_status(sid: str, **fields):
    """部分更新任务状态：读取现有数据 → 合并字段 → 写回。"""
    current = await get_task_status(sid)
    if current is None:
        return
    current.update(fields)
    await redis.set(_key_status(sid), json.dumps(current, ensure_ascii=False), ex=SESSION_TTL)


async def append_event(sid: str, event: dict):
    """Agent 事件逐条 rpush，保留最近 200 条。"""
    await redis.rpush(_key_events(sid), json.dumps(event, ensure_ascii=False))
    # 截断保留最近 200 条
    await redis.ltrim(_key_events(sid), -200, -1)
    await redis.expire(_key_events(sid), SESSION_TTL)


async def set_state(sid: str, key: str, value: str):
    """Agent 间传递的状态快照（Hash）。"""
    await redis.hset(_key_state(sid), key, value)
    await redis.expire(_key_state(sid), SESSION_TTL)


async def get_state(sid: str) -> dict:
    raw = await redis.hgetall(_key_state(sid))
    return raw or {}
