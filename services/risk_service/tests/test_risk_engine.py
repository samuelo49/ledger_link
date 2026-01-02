from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from services.risk_service.app.models.risk_rule import RiskDecision, RiskRuleType
from services.risk_service.app.risk_engine import EvaluationContext, RiskEngine


@dataclass
class DummyRule:
    id: int
    name: str
    rule_type: RiskRuleType
    action: RiskDecision
    event_types: list[str]
    config: dict | None = None
    weight: float = 1.0
    enabled: bool = True


def test_amount_threshold_triggers_review():
    rule = DummyRule(
        id=1,
        name="high_value",
        rule_type=RiskRuleType.amount_threshold,
        action=RiskDecision.review,
        event_types=["payment_intent_confirm"],
        config={"thresholds": {"USD": "5000"}},
    )
    engine = RiskEngine([rule])
    ctx = EvaluationContext(
        event_type="payment_intent_confirm",
        subject_id="pi-1",
        user_id="user-1",
        amount=Decimal("7500"),
        currency="USD",
        metadata={},
    )
    result = engine.evaluate(ctx)
    assert result.decision == RiskDecision.review
    assert result.triggered_rules
    assert "amount" in result.triggered_rules[0].reason


def test_country_mismatch_and_blocklist_escalation():
    mismatch = DummyRule(
        id=2,
        name="mismatch",
        rule_type=RiskRuleType.country_mismatch,
        action=RiskDecision.review,
        event_types=["wallet_transaction"],
        config={},
    )
    blocklist = DummyRule(
        id=3,
        name="embargo",
        rule_type=RiskRuleType.blocklist_country,
        action=RiskDecision.decline,
        event_types=["wallet_transaction"],
        config={"blocked": ["RU", "IR"]},
        weight=5.0,
    )
    engine = RiskEngine([mismatch, blocklist])
    ctx = EvaluationContext(
        event_type="wallet_transaction",
        subject_id="wallet-1",
        user_id="user-2",
        amount=Decimal("100"),
        currency="USD",
        metadata={"ip_country": "IR", "user_country": "US"},
    )
    result = engine.evaluate(ctx)
    assert result.decision == RiskDecision.decline
    assert len(result.triggered_rules) == 2


def test_no_matching_rules_default_to_approve():
    engine = RiskEngine([])
    ctx = EvaluationContext(
        event_type="payment_intent_confirm",
        subject_id="pi-2",
        user_id="user-3",
        amount=Decimal("10"),
        currency="USD",
        metadata={},
    )
    result = engine.evaluate(ctx)
    assert result.decision == RiskDecision.approve
    assert result.triggered_rules == []
