from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..settings import identity_settings

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    settings = identity_settings()
    return {"status": "ok", "service": settings.service_name}


@router.get("/metrics")
async def metrics() -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
