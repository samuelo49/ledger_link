from __future__ import annotations

from collections import deque
from typing import Callable, Deque

import httpx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from services.api_gateway.app.main import create_app


class StubAsyncClient:
    def __init__(self, handler: Callable[..., httpx.Response]):
        self._handler = handler

    async def __aenter__(self) -> StubAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        return None

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self._handler("POST", url, **kwargs)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self._handler("GET", url, **kwargs)


@pytest_asyncio.fixture()
async def gateway_test_client(monkeypatch):
    # Prevent OTEL setup noise in tests
    monkeypatch.setattr("services.api_gateway.app.main.setup_instrumentation", lambda app: None)

    records: Deque[dict] = deque()
    responses: dict[tuple[str, str], tuple[int, dict | None, bytes | None]] = {}

    def queue_response(method: str, url: str, *, status: int = 200, json_body: dict | None = None) -> None:
        responses[(method, url)] = (status, json_body, None)

    async def handler(method: str, url: str, **kwargs) -> httpx.Response:
        records.append({"method": method, "url": url, "kwargs": kwargs})
        status, json_body, content = responses[(method, url)]
        request = httpx.Request(method, url)
        if json_body is not None:
            return httpx.Response(status, json=json_body, request=request)
        return httpx.Response(status, content=content or b"", request=request)

    for target in [
        "services.api_gateway.app.routes.identity.httpx.AsyncClient",
        "services.api_gateway.app.routes.wallet.httpx.AsyncClient",
    ]:
        monkeypatch.setattr(target, lambda *args, **kwargs: StubAsyncClient(handler))

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, queue_response, records


@pytest.mark.asyncio
async def test_identity_proxy_forwards_headers(gateway_test_client):
    client, queue_response, records = gateway_test_client
    upstream_url = "http://identity-service:8000/api/v1/auth/register"
    queue_response("POST", upstream_url, status=201, json_body={"status": "created"})

    headers = {
        "Authorization": "Bearer abc",
        "Content-Type": "application/json",
        "X-Request-Id": "req-123",
        "X-Forbidden": "drop-me",
    }
    payload = {"email": "test@example.com", "password": "Passw0rd!"}
    response = await client.post("/api/v1/auth/register", json=payload, headers=headers)
    assert response.status_code == 201
    assert response.json()["status"] == "created"

    record = records.pop()
    forwarded_headers = record["kwargs"]["headers"]
    # httpx normalizes header keys to lowercase; compare case-insensitively.
    normalized = {k.lower(): v for k, v in forwarded_headers.items()}
    assert normalized.get("authorization") == "Bearer abc"
    assert "x-forbidden" not in normalized


@pytest.mark.asyncio
async def test_wallet_proxy_forwards_bearer_token(gateway_test_client):
    client, queue_response, records = gateway_test_client
    upstream_url = "http://wallet-service:8000/api/v1/wallets/10/balance"
    queue_response("GET", upstream_url, status=200, json_body={"id": 10, "balance": "50.00"})

    response = await client.get(
        "/api/v1/wallets/10/balance",
        headers={"Authorization": "Bearer access-token"},
    )
    assert response.status_code == 200
    assert response.json()["balance"] == "50.00"

    record = records.pop()
    forwarded_headers = record["kwargs"]["headers"]
    normalized = {k.lower(): v for k, v in forwarded_headers.items()}
    assert normalized.get("authorization") == "Bearer access-token"
