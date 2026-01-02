from __future__ import annotations

import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.payments_service.app.db.base import Base
from services.payments_service.app.dependencies import get_current_user_id, get_session
from services.payments_service.app.main import create_app
from services.payments_service.app import settings as payments_settings_module


def _asgi_client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


class StubAsyncClient:
    def __init__(self, handler):
        self._handler = handler

    async def __aenter__(self) -> StubAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: D401
        return None

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self._handler("POST", url, **kwargs)


@pytest_asyncio.fixture()
async def payments_test_app(monkeypatch):
    payments_settings_module.payments_settings.cache_clear()

    async def fake_run_migrations(*_args, **_kwargs) -> None:  # pragma: no cover
        return None

    monkeypatch.setattr(
        "services.payments_service.app.main.run_alembic_migrations",
        fake_run_migrations,
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_session() -> AsyncSession:
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()

    def _override_current_user() -> int:
        return 99

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user_id] = _override_current_user

    state: dict[str, str | int] = {
        "risk_decision": "approve",
        "risk_status": 200,
        "wallet_status": 200,
    }

    async def handler(method: str, url: str, **kwargs) -> httpx.Response:
        if "risk-service" in url:
            decision = state["risk_decision"]
            status = state["risk_status"]
            return httpx.Response(
                status,
                json={"decision": decision},
                request=httpx.Request(method, url),
            )
        if "wallet-service" in url:
            status = state["wallet_status"]
            return httpx.Response(status, json={"ok": True}, request=httpx.Request(method, url))
        raise RuntimeError(f"Unhandled URL {url}")

    monkeypatch.setattr(
        "services.payments_service.app.routes.payment_intents.httpx.AsyncClient",
        lambda *args, **kwargs: StubAsyncClient(handler),
    )

    yield app, state

    await engine.dispose()
    payments_settings_module.payments_settings.cache_clear()


@pytest.mark.asyncio
async def test_confirm_intent_success(payments_test_app):
    app, state = payments_test_app
    async with _asgi_client(app) as client:
        create = await client.post(
            "/api/v1/payments/intents",
            json={"wallet_id": 1, "amount": "100.00", "currency": "USD"},
        )
        assert create.status_code == 201, create.text
        intent_id = create.json()["id"]

        response = await client.post(f"/api/v1/payments/intents/{intent_id}/confirm", json={})
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"


@pytest.mark.asyncio
async def test_confirm_blocked_by_risk(payments_test_app):
    app, state = payments_test_app
    state["risk_decision"] = "decline"
    async with _asgi_client(app) as client:
        create = await client.post(
            "/api/v1/payments/intents",
            json={"wallet_id": 1, "amount": "100.00", "currency": "USD"},
        )
        assert create.status_code == 201, create.text
        intent_id = create.json()["id"]
        response = await client.post(f"/api/v1/payments/intents/{intent_id}/confirm", json={})
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_confirm_requires_review(payments_test_app):
    app, state = payments_test_app
    state["risk_decision"] = "review"
    async with _asgi_client(app) as client:
        create = await client.post(
            "/api/v1/payments/intents",
            json={"wallet_id": 1, "amount": "50.00", "currency": "USD"},
        )
        assert create.status_code == 201, create.text
        intent_id = create.json()["id"]
        response = await client.post(f"/api/v1/payments/intents/{intent_id}/confirm", json={})
        assert response.status_code == 409


@pytest.mark.asyncio
async def test_wallet_debit_failure_propagates(payments_test_app):
    app, state = payments_test_app
    state["risk_decision"] = "approve"
    state["wallet_status"] = 409
    async with _asgi_client(app) as client:
        create = await client.post(
            "/api/v1/payments/intents",
            json={"wallet_id": 1, "amount": "25.00", "currency": "USD"},
        )
        assert create.status_code == 201, create.text
        intent_id = create.json()["id"]
        response = await client.post(f"/api/v1/payments/intents/{intent_id}/confirm", json={})
        assert response.status_code == 409
