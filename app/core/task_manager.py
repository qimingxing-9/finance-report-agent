import asyncio
import logging
from datetime import datetime, timezone

from app.storage.redis_client import (
    append_event,
    set_task_status,
    update_task_status,
)

logger = logging.getLogger(__name__)

# 流水线 Agent 名称（阶段二占位，阶段四接入真实 Agent）
PIPELINE_AGENTS = ["pdf_parser", "metric_extractor", "risk_checker", "report_writer"]


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
    from app.storage.redis_client import get_task_status
    return await get_task_status(session_id)


def start_pipeline_task(session_id: str):
    """创建后台 asyncio 任务，启动流水线。"""
    task = asyncio.create_task(_run_pipeline(session_id))
    task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    logger.info("Pipeline task started for session %s", session_id)


async def _run_pipeline(session_id: str):
    """后台流水线执行：pending → running → 逐 Agent 执行 → success / failed。

    阶段二：模拟 Agent 执行（sleep），阶段四替换为真实 ADK Agent 调用。
    """
    try:
        # pending → running
        await update_task_status(session_id, status="running")
        await append_event(session_id, {
            "agent": None,
            "event": "pipeline_started",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Session %s: pipeline started", session_id)

        # 逐个 Agent 执行
        for i, agent_name in enumerate(PIPELINE_AGENTS):
            await update_task_status(
                session_id,
                current_agent=agent_name,
                progress=i,
            )
            await append_event(session_id, {
                "agent": agent_name,
                "event": "agent_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            logger.info("Session %s: agent %s started (step %d/%d)",
                        session_id, agent_name, i + 1, len(PIPELINE_AGENTS))

            # --- 阶段二占位：模拟 Agent 执行 ---
            # 阶段四这里替换为：async for event in runner.run_async(...):
            await asyncio.sleep(2)

            await append_event(session_id, {
                "agent": agent_name,
                "event": "agent_completed",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        # 全部完成 → success
        await update_task_status(
            session_id,
            status="success",
            current_agent=None,
            progress=len(PIPELINE_AGENTS),
            report_id=None,  # 阶段五接入报告生成后回填
        )
        await append_event(session_id, {
            "agent": None,
            "event": "pipeline_completed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Session %s: pipeline completed", session_id)

    except Exception as e:
        # 异常 → failed
        logger.exception("Session %s: pipeline failed", session_id)
        await update_task_status(
            session_id,
            status="failed",
            error=str(e),
        )
        await append_event(session_id, {
            "agent": None,
            "event": "pipeline_failed",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
