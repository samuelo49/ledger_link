from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..settings import gateway_settings

router = APIRouter()


@router.get("/healthz")
async def health_check() -> dict[str, str]:
    settings = gateway_settings()
    return {"status": "ok", "service": "api-gateway", "issuer": settings.jwt_issuer}


@router.get("/api/v1/healthz")
async def health_check_v1() -> dict[str, str]:
    return await health_check()


@router.get("/api/v1/metrics")
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
