from fastapi import FastAPI, HTTPException, Response
from contextlib import asynccontextmanager
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT_DIR / "libs" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.append(str(SHARED_SRC))

from shared.request_context import RequestIDMiddleware
from shared.errors import http_exception_handler, unhandled_exception_handler

from .settings import payments_settings
from .alembic_helper import run_alembic_migrations
from .startup import setup_instrumentation
from .routes.payment_intents import router as payment_intents_router
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_alembic_migrations(payments_settings().sync_db_url)
    except Exception as e:
        print(f"Migration failed...{e}")
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Payments Service", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(payment_intents_router, prefix="/api/v1")

    @app.get("/api/v1/healthz")
    async def healthz() -> dict[str, str]:  # noqa: D401
        return {"status": "ok"}

    @app.get("/api/v1/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    setup_instrumentation(app)
    return app
