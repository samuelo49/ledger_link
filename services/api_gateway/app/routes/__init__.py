"""Route registration for the API Gateway.

Aggregates and mounts all routers under a single root for the application.
"""

from fastapi import APIRouter, FastAPI

from . import health, identity, wallet, payments, catalog


def register_routes(app: FastAPI) -> None:
    """Register system, auth, wallet, and payments routers on the app."""
    router = APIRouter()
    router.include_router(health.router, tags=["system"])
    router.include_router(identity.router, tags=["auth"])
    router.include_router(wallet.router, tags=["wallets"])
    router.include_router(payments.router, tags=["payments"])
    router.include_router(catalog.router, tags=["catalog"])
    app.include_router(router)
