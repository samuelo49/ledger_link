import pytest
from httpx import AsyncClient

from services.identity_service.app import app


@pytest.mark.anyio
async def test_health_endpoint() -> None:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
