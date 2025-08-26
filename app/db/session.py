from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


_engine: AsyncEngine | None = None
_SessionLocal: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        # MySQL/MariaDB via asyncmy, recommended pool_pre_ping to detect dead connections
        _engine = create_async_engine(
            settings.db_url,
            pool_pre_ping=True,
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
        )
    return _SessionLocal


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-style dependency (usable in services/handlers too)."""
    SessionLocal = get_session_maker()
    async with SessionLocal() as session:
        yield session
