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
