from fastapi import FastAPI
from contextlib import asynccontextmanager

from .settings import payments_settings
from .alembic_helper import run_alembic_migrations
from .startup import setup_instrumentation
from .routes.payment_intents import router as payment_intents_router
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await run_alembic_migrations(payments_settings().sync_db_url)
    except Exception:
        pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Payments Service", version="0.1.0", lifespan=lifespan)
    app.include_router(payment_intents_router)

    @app.get("/api/v1/healthz")
    async def healthz() -> dict[str, str]:  # noqa: D401
        return {"status": "ok"}

    @app.get("/api/v1/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    setup_instrumentation(app)
    return app
