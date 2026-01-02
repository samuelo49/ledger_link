from fastapi import FastAPI, HTTPException
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[3]
SHARED_SRC = ROOT_DIR / "libs" / "shared" / "src"
if str(SHARED_SRC) not in sys.path:
    sys.path.append(str(SHARED_SRC))

from shared.errors import http_exception_handler, unhandled_exception_handler

from .middleware import setup_middleware
from .routes import register_routes
from .startup import setup_instrumentation


def create_app() -> FastAPI:
    app = FastAPI(title="Fintech API Gateway", version="0.1.0")
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    setup_middleware(app)
    register_routes(app)
    # Configure tracing last so routes/middleware are already attached
    setup_instrumentation(app)
    return app
