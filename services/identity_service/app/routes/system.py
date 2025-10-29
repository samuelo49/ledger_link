from fastapi import APIRouter

from ..settings import identity_settings

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    settings = identity_settings()
    return {"status": "ok", "service": settings.service_name}
