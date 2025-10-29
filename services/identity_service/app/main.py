from fastapi import FastAPI

from .routes import register_routes
from .startup import setup_instrumentation, setup_logging


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="Identity Service", version="0.1.0")
    setup_instrumentation(app)
    register_routes(app)
    return app
