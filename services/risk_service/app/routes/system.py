from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..metrics import risk_health_checks_total

router = APIRouter()


@router.get("/api/v1/healthz")
async def healthz() -> dict[str, str]:
    """Basic readiness endpoint with a Prometheus counter for observability."""
    risk_health_checks_total.inc()
    return {"status": "ok", "service": "risk"}


@router.get("/api/v1/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics for the risk service."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
