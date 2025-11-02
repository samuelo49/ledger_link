from fastapi import APIRouter, FastAPI

from .wallet import router as wallet_router
from . import system


def register_routes(app: FastAPI) -> None:
    router = APIRouter(prefix="/api/v1")
    router.include_router(wallet_router, prefix="/wallets", tags=["wallets"])
    router.include_router(system.router, tags=["system"])
    app.include_router(router)
