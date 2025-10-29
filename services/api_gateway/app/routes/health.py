from fastapi import APIRouter

from ..settings import gateway_settings

router = APIRouter()


@router.get("/healthz")
async def health_check() -> dict[str, str]:
    settings = gateway_settings()
    return {"status": "ok", "service": "api-gateway", "issuer": settings.jwt_issuer}
