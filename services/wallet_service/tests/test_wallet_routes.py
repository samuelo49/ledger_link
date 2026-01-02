from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.wallet_service.app.db.base import Base
from services.wallet_service.app.dependencies import get_current_user_id, get_session
from services.wallet_service.app.main import create_app
from services.wallet_service.app import settings as wallet_settings_module


def _asgi_client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://testserver")


@pytest_asyncio.fixture()
async def wallet_test_app(monkeypatch):
    wallet_settings_module.wallet_settings.cache_clear()
    monkeypatch.setenv("WALLET_RISK_CHECKS_ENABLED", "false")

    async def fake_run_migrations(*_args, **_kwargs) -> None:  # pragma: no cover - helper
        return None

    monkeypatch.setattr(
        "services.wallet_service.app.main.run_alembic_migrations",
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
        return 42

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    app.dependency_overrides[get_current_user_id] = _override_current_user
    yield app

    await engine.dispose()
    wallet_settings_module.wallet_settings.cache_clear()
    monkeypatch.delenv("WALLET_RISK_CHECKS_ENABLED", raising=False)


@pytest.mark.asyncio
async def test_wallet_create_is_idempotent(wallet_test_app):
    async with _asgi_client(wallet_test_app) as client:
        payload = {"currency": "USD"}
        first = await client.post("/api/v1/wallets/", json=payload)
        assert first.status_code == 201
        second = await client.post("/api/v1/wallets/", json=payload)
        assert second.status_code == 200  # existing wallet returned
        assert first.json()["id"] == second.json()["id"]


@pytest.mark.asyncio
async def test_credit_debit_and_insufficient_funds(wallet_test_app):
    async with _asgi_client(wallet_test_app) as client:
        create = await client.post("/api/v1/wallets/", json={"currency": "USD"})
        wallet_id = create.json()["id"]

        credit_payload = {"amount": "100.00", "idempotency_key": "credit-1"}
        credit = await client.post(f"/api/v1/wallets/{wallet_id}/credit", json=credit_payload)
        assert credit.status_code == 200
        assert Decimal(str(credit.json()["balance"])) == Decimal("100.00")

        # Replay with same idempotency key should be ignored
        replay = await client.post(f"/api/v1/wallets/{wallet_id}/credit", json=credit_payload)
        assert Decimal(str(replay.json()["balance"])) == Decimal("100.00")

        debit = await client.post(
            f"/api/v1/wallets/{wallet_id}/debit",
            json={"amount": "40.00"},
        )
        assert debit.status_code == 200
        assert Decimal(str(debit.json()["balance"])) == Decimal("60.00")

        insufficient = await client.post(
            f"/api/v1/wallets/{wallet_id}/debit",
            json={"amount": "100.00"},
        )
        assert insufficient.status_code == 409
