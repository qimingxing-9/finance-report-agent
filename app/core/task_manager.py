from datetime import datetime, timezone

from app.storage.redis_client import get_task_status, set_task_status


async def init_task_status(session_id: str):
    """上传成功后调用：Redis 写入初始状态 pending。"""
    await set_task_status(
        sid=session_id,
        status="pending",
        current_agent=None,
        progress=0,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


async def read_task_status(session_id: str) -> dict | None:
    """读取任务状态，供 status 接口返回。"""
    return await get_task_status(session_id)
