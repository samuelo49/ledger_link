from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from services.identity_service.app.settings import identity_settings


def build_engine() -> AsyncEngine:
    settings = identity_settings()
    engine = create_async_engine(
        settings.async_db_url,
        echo=False,
        pool_pre_ping=True,
    )
    return engine


async_engine = build_engine()
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
