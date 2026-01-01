from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..settings import risk_settings

_engine = create_async_engine(risk_settings().async_db_url, echo=False, future=True)
async_session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False, class_=AsyncSession)
