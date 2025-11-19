from fastapi import FastAPI
from contextlib import asynccontextmanager

from .settings import wallet_settings
from .alembic_helper import run_alembic_migrations
from .routes import register_routes
from .startup import setup_instrumentation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run DB migrations on startup (best-effort)
    try:
        await run_alembic_migrations(wallet_settings().sync_db_url)
    except Exception:
        # Keep the service up even if migrations fail locally
        pass
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Wallet Service", version="0.1.0", lifespan=lifespan)
    register_routes(app)
    setup_instrumentation(app)
    return app
