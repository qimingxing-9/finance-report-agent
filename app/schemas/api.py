from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    msg: str = ""
    data: T | None = None


class UploadResponseData(BaseModel):
    session_id: str
    status: str = "pending"


class StatusResponseData(BaseModel):
    session_id: str
    status: str
    current_agent: str | None = None
    progress: int = 0
    total: int = 4
    error: str | None = None
    report_id: str | None = None
    created_at: str | None = None
