"""Risk service routers."""

from .system import router as system_router
from .risk import router as risk_router

__all__ = ["system_router", "risk_router"]
