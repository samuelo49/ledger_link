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

from .routes import register_routes
from .startup import setup_instrumentation, setup_logging, init_service_startup, shutdown_instrumentation


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Perform async initialization tasks before the app starts serving requests
    await init_service_startup(app)
    yield
    # Perform async cleanup tasks when the app is shutting down
    await shutdown_instrumentation(app)


def create_app() -> FastAPI:
    # Set up logging configuration before creating the FastAPI app instance
    setup_logging()
    # Create the FastAPI app with a defined lifespan context manager handling startup and shutdown
    app = FastAPI(title="Identity Service", version="0.1.0", lifespan=lifespan)
    # Initialize instrumentation such as metrics, tracing, or monitoring
    setup_instrumentation(app)
    app.add_middleware(RequestIDMiddleware)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    register_routes(app)
    return app

# Explicitly create the FastAPI app instance to be used by ASGI servers
app = create_app()
