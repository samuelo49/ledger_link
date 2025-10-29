from fastapi import APIRouter, FastAPI

from . import health


def register_routes(app: FastAPI) -> None:
    router = APIRouter()
    router.include_router(health.router, tags=["system"])
    app.include_router(router)
