from fastapi import APIRouter, FastAPI

from .wallet import router as wallet_router


def register_routes(app: FastAPI) -> None:
    router = APIRouter(prefix="/api/v1")
    router.include_router(wallet_router, prefix="/wallets", tags=["wallets"])
    app.include_router(router)
