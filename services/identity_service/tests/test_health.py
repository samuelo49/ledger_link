import pytest
from httpx import ASGITransport, AsyncClient

from services.identity_service.app import app


@pytest.mark.anyio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
