from fastapi import APIRouter, FastAPI

from . import auth, system


def register_routes(app: FastAPI) -> None:
    router = APIRouter(prefix="/api/v1")
    router.include_router(system.router, tags=["system"])
    router.include_router(auth.router, tags=["auth"])
    app.include_router(router)
