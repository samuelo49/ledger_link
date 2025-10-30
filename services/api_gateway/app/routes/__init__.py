from fastapi import APIRouter, FastAPI

from . import health, identity


def register_routes(app: FastAPI) -> None:
    router = APIRouter()
    router.include_router(health.router, tags=["system"])
    router.include_router(identity.router, tags=["auth"])
    app.include_router(router)
