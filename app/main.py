import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.report import router as report_router
from app.storage.mysql import init_tables

os.makedirs("uploads", exist_ok=True)
os.makedirs("reports", exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建表
    await init_tables()
    yield
    # 关闭：无需特殊清理


app = FastAPI(title="金融财报多-Agent 智能分析平台", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(report_router)
