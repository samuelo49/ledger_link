from fastapi import FastAPI

from .middleware import setup_middleware
from .routes import register_routes


def create_app() -> FastAPI:
    app = FastAPI(title="Fintech API Gateway", version="0.1.0")
    setup_middleware(app)
    register_routes(app)
    return app
