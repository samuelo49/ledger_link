from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT_DIR / "libs" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.append(str(SHARED_SRC))

from shared.request_context import RequestIDMiddleware
from shared.errors import http_exception_handler, unhandled_exception_handler

from .settings import risk_settings
from .alembic_helper import run_alembic_migrations
from .routes.system import router as system_router
from .routes.risk import router as risk_router
from .metrics import risk_service_startup_total, risk_service_migration_total
from .db.session import async_session_factory
from .db.seed_rules import seed_default_rules


@asynccontextmanager
async def lifespan(app: FastAPI):
    risk_service_startup_total.inc()
    try:
        await run_alembic_migrations(risk_settings().sync_db_url)
        risk_service_migration_total.labels(outcome="success").inc()
    except Exception:
        risk_service_migration_total.labels(outcome="failed").inc()

    async with async_session_factory() as session:
        await seed_default_rules(session)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Risk Service", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(system_router)
    app.include_router(risk_router)
    return app
