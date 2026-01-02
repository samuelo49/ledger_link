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
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    register_routes(app)
    setup_instrumentation(app)
    return app
