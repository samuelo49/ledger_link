from fastapi import FastAPI
from contextlib import asynccontextmanager

from .settings import risk_settings
from .alembic_helper import run_alembic_migrations
from .routes.system import router as system_router
from .metrics import risk_service_startup_total, risk_service_migration_total


@asynccontextmanager
async def lifespan(app: FastAPI):
    risk_service_startup_total.inc()
    try:
        await run_alembic_migrations(risk_settings().sync_db_url)
        risk_service_migration_total.labels(outcome="success").inc()
    except Exception:
        risk_service_migration_total.labels(outcome="failed").inc()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Risk Service", version="0.1.0", lifespan=lifespan)
    app.include_router(system_router)
    return app
