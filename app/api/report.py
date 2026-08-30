import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_manager import init_task_status, read_task_status, start_pipeline_task
from app.schemas.api import ApiResponse, StatusResponseData, UploadResponseData
from app.storage.mysql import get_db
from app.storage.models import ReportInfo

router = APIRouter(prefix="/api/report", tags=["report"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/upload", response_model=ApiResponse[UploadResponseData])
async def upload_report(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # 校验文件类型
    if not file.content_type or "pdf" not in file.content_type:
        return ApiResponse(code=1001, msg="文件格式不支持，请上传 PDF")

    # 读取内容并校验大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return ApiResponse(code=1002, msg="文件大小超过 20MB 限制")

    # 生成 session_id
    session_id = str(uuid.uuid4())
    file_name = file.filename or f"{session_id}.pdf"
    file_path = f"uploads/{session_id}.pdf"

    # 落盘
    with open(file_path, "wb") as f:
        f.write(content)

    # 写 MySQL
    record = ReportInfo(
        session_id=session_id,
        file_name=file_name,
        file_path=file_path,
    )
    db.add(record)
    await db.commit()

    # Redis 初始化任务状态
    await init_task_status(session_id)

    # 启动后台流水线任务
    start_pipeline_task(session_id)

    return ApiResponse(
        data=UploadResponseData(session_id=session_id, status="pending")
    )


@router.get("/status/{session_id}", response_model=ApiResponse[StatusResponseData])
async def get_status(session_id: str):
    status_data = await read_task_status(session_id)
    if status_data is None:
        return ApiResponse(code=2001, msg="session 不存在")

    return ApiResponse(data=StatusResponseData(**status_data))
