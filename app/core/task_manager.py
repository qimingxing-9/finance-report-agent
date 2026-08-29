# app/core/task_manager.py — 后台任务 + 状态机
# - asyncio.create_task 启动流水线
# - 任务状态机：pending → running → success / failed
# - 异常捕获 + 状态回写 Redis
