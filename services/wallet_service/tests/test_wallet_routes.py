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


async def _create_wallet(client: AsyncClient, currency: str = "USD", allow_additional: bool = False) -> dict:
    response = await client.post("/api/v1/wallets/", json={"currency": currency, "allow_additional": allow_additional})
    assert response.status_code in {200, 201}
    return response.json()


async def _seed_balance(client: AsyncClient, wallet_id: int, amount: str, key: str) -> None:
    payload = {"amount": amount, "idempotency_key": key}
    response = await client.post(f"/api/v1/wallets/{wallet_id}/credit", json=payload)
    assert response.status_code == 200


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
        wallet = await _create_wallet(client)
        wallet_id = wallet["id"]

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


@pytest.mark.asyncio
async def test_transfer_between_wallets_is_idempotent(wallet_test_app):
    async with _asgi_client(wallet_test_app) as client:
        source = await _create_wallet(client)
        target = await _create_wallet(client, allow_additional=True)
        await _seed_balance(client, source["id"], "75.00", "seed-credit")

        payload = {
            "target_wallet_id": target["id"],
            "amount": "25.00",
            "currency": "USD",
            "idempotency_key": "transfer-001",
            "description": "peer transfer",
        }
        first = await client.post(f"/api/v1/wallets/{source['id']}/transfers", json=payload)
        assert first.status_code == 201
        data = first.json()
        assert Decimal(str(data["source_wallet"]["balance"])) == Decimal("50.00")
        assert Decimal(str(data["target_wallet"]["balance"])) == Decimal("25.00")

        replay = await client.post(f"/api/v1/wallets/{source['id']}/transfers", json=payload)
        replay_data = replay.json()
        assert Decimal(str(replay_data["source_wallet"]["balance"])) == Decimal("50.00")
        assert Decimal(str(replay_data["target_wallet"]["balance"])) == Decimal("25.00")


@pytest.mark.asyncio
async def test_hold_lifecycle_preserves_invariants(wallet_test_app):
    async with _asgi_client(wallet_test_app) as client:
        wallet = await _create_wallet(client)
        wallet_id = wallet["id"]
        await _seed_balance(client, wallet_id, "60.00", "hold-seed")

        create_payload = {"amount": "15.00", "idempotency_key": "hold-1", "reference": "auth-123"}
        hold_resp = await client.post(f"/api/v1/wallets/{wallet_id}/holds", json=create_payload)
        assert hold_resp.status_code == 201
        hold = hold_resp.json()
        assert hold["status"] == "active"

        balance = await client.get(f"/api/v1/wallets/{wallet_id}/balance")
        assert Decimal(str(balance.json()["balance"])) == Decimal("45.00")

        release = await client.post(
            f"/api/v1/wallets/{wallet_id}/holds/{hold['id']}/release",
            json={"idempotency_key": "release-1"},
        )
        assert release.status_code == 200
        assert release.json()["status"] == "released"

        balance_after_release = await client.get(f"/api/v1/wallets/{wallet_id}/balance")
        assert Decimal(str(balance_after_release.json()["balance"])) == Decimal("60.00")

        replay_release = await client.post(
            f"/api/v1/wallets/{wallet_id}/holds/{hold['id']}/release",
            json={"idempotency_key": "release-1"},
        )
        assert replay_release.status_code == 200

        hold2_payload = {"amount": "10.00", "idempotency_key": "hold-2"}
        hold2 = await client.post(f"/api/v1/wallets/{wallet_id}/holds", json=hold2_payload)
        capture = await client.post(f"/api/v1/wallets/{wallet_id}/holds/{hold2.json()['id']}/capture")
        assert capture.status_code == 200
        assert capture.json()["status"] == "captured"

        # Captured hold keeps funds withdrawn
        final_balance = await client.get(f"/api/v1/wallets/{wallet_id}/balance")
        assert Decimal(str(final_balance.json()["balance"])) == Decimal("50.00")


@pytest.mark.asyncio
async def test_statements_paginate_and_require_ownership(wallet_test_app):
    async with _asgi_client(wallet_test_app) as client:
        wallet = await _create_wallet(client)
        wallet_id = wallet["id"]
        await _seed_balance(client, wallet_id, "30.00", "ledger-seed")
        await client.post(
            f"/api/v1/wallets/{wallet_id}/debit",
            json={"amount": "5.00", "idempotency_key": "ledger-debit"},
        )

        first_page = await client.get(f"/api/v1/wallets/{wallet_id}/statements", params={"limit": 1})
        assert first_page.status_code == 200
        first_data = first_page.json()
        assert first_data["wallet_id"] == wallet_id
        assert len(first_data["entries"]) == 1
        cursor = first_data["next_cursor"]
        assert cursor is not None

        second_page = await client.get(
            f"/api/v1/wallets/{wallet_id}/statements",
            params={"limit": 1, "cursor": cursor},
        )
        assert second_page.status_code == 200
        second_data = second_page.json()
        assert len(second_data["entries"]) == 1

        missing = await client.get("/api/v1/wallets/9999/statements")
        assert missing.status_code == 404
