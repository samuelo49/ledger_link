from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.risk_service.app.db.base import Base
from services.risk_service.app.dependencies import get_session
from services.risk_service.app.main import create_app
from services.risk_service.app.models import RiskRule, RiskRuleType, RiskDecision, RiskEvaluation
from services.risk_service.app import settings as risk_settings_module


@pytest_asyncio.fixture()
async def risk_test_context(monkeypatch):
    risk_settings_module.risk_settings.cache_clear()

    async def fake_run_migrations(*_args, **_kwargs) -> None:  # pragma: no cover
        return None

    monkeypatch.setattr(
        "services.risk_service.app.main.run_alembic_migrations",
        fake_run_migrations,
    )
    monkeypatch.setattr(
        "services.risk_service.app.main.seed_default_rules",
        lambda *args, **kwargs: None,
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

    app = create_app()
    app.dependency_overrides[get_session] = _override_session
    yield app, session_factory

    await engine.dispose()
    risk_settings_module.risk_settings.cache_clear()


@pytest.mark.asyncio
async def test_list_rules_and_evaluate(risk_test_context):
    app, session_factory = risk_test_context

    async with session_factory() as session:
        session.add(
            RiskRule(
                name="high_value_payment",
                description="Review large payments",
                event_types=["payment_intent_confirm"],
                rule_type=RiskRuleType.amount_threshold,
                action=RiskDecision.review,
                config={"thresholds": {"USD": "5000"}},
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        rules = await client.get("/api/v1/risk/rules")
        assert rules.status_code == 200
        assert len(rules.json()) == 1

        evaluation = await client.post(
            "/api/v1/risk/evaluations",
            json={
                "event_type": "payment_intent_confirm",
                "subject_id": "pi-123",
                "user_id": "user-5",
                "amount": "7500",
                "currency": "USD",
                "metadata": {},
            },
        )
        assert evaluation.status_code == 201
        body = evaluation.json()
        assert body["decision"] in {"review", "decline"}

    async with session_factory() as session:
        stored = await session.scalar(select(RiskEvaluation).where(RiskEvaluation.subject_id == "pi-123"))
        assert stored is not None
