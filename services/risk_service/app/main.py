from fastapi import FastAPI
from contextlib import asynccontextmanager

from .settings import risk_settings
from .alembic_helper import run_alembic_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_alembic_migrations(risk_settings().sync_db_url)
    except Exception:
        pass
    yield


def create_app() -> FastAPI:
    return FastAPI(title="Risk Service", version="0.1.0", lifespan=lifespan)
