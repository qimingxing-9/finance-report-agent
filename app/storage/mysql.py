from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.storage.models import Base

engine = create_async_engine(settings.mysql_url, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def init_tables():
    """启动时自动建表（开发环境用，生产环境用 sql/init.sql）。"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
