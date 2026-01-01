from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

from .models import RiskRule, RiskDecision, RiskRuleType


@dataclass
class TriggeredRule:
    rule_id: int
    name: str
    action: RiskDecision
    reason: str
    weight: float


@dataclass
class EvaluationResult:
    decision: RiskDecision
    risk_score: float
    triggered_rules: list[TriggeredRule]


@dataclass
class EvaluationContext:
    event_type: str
    subject_id: str
    user_id: str
    amount: Decimal
    currency: str
    metadata: dict[str, Any]


class RiskEngine:
    """Executes configured risk rules for a context and aggregates a decision."""

    def __init__(self, rules: Iterable[RiskRule]) -> None:
        self.rules = list(rules)

    def evaluate(self, ctx: EvaluationContext) -> EvaluationResult:
        decision = RiskDecision.approve
        score = 0.0
        triggered: list[TriggeredRule] = []

        for rule in self.rules:
            if ctx.event_type not in (rule.event_types or []):
                continue
            trigger = _evaluate_rule(rule, ctx)
            if not trigger:
                continue
            triggered.append(trigger)
            score += trigger.weight
            decision = _escalate(decision, trigger.action)

        return EvaluationResult(decision=decision, risk_score=score, triggered_rules=triggered)


def _evaluate_rule(rule: RiskRule, ctx: EvaluationContext) -> TriggeredRule | None:
    if not rule.enabled:
        return None
    config = rule.config or {}
    if rule.rule_type == RiskRuleType.amount_threshold:
        thresholds = config.get("thresholds") or {}
        default_threshold = Decimal(str(thresholds.get("default", thresholds.get("value", "0"))))
        currency_threshold = Decimal(str(thresholds.get(ctx.currency, default_threshold)))
        if ctx.amount >= currency_threshold:
            reason = f"amount {ctx.amount} {ctx.currency} >= {currency_threshold}"
            return TriggeredRule(rule.id, rule.name, rule.action, reason, rule.weight)
        return None
    if rule.rule_type == RiskRuleType.country_mismatch:
        ip_country = (ctx.metadata.get("ip_country") or "").upper()
        user_country = (ctx.metadata.get("user_country") or "").upper()
        if ip_country and user_country and ip_country != user_country:
            reason = f"ip_country {ip_country} != user_country {user_country}"
            return TriggeredRule(rule.id, rule.name, rule.action, reason, rule.weight)
        return None
    if rule.rule_type == RiskRuleType.blocklist_country:
        blocked = {c.upper() for c in config.get("blocked", [])}
        ip_country = (ctx.metadata.get("ip_country") or "").upper()
        if ip_country and ip_country in blocked:
            reason = f"ip_country {ip_country} is blocked"
            return TriggeredRule(rule.id, rule.name, rule.action, reason, rule.weight)
        return None
    if rule.rule_type == RiskRuleType.email_domain_block:
        blocklist = {d.lower() for d in config.get("domains", [])}
        email_domain = (ctx.metadata.get("email_domain") or "").lower()
        if email_domain and email_domain in blocklist:
            reason = f"email domain {email_domain} is blocklisted"
            return TriggeredRule(rule.id, rule.name, rule.action, reason, rule.weight)
        return None
    return None


def _escalate(current: RiskDecision, triggered: RiskDecision) -> RiskDecision:
    order = {
        RiskDecision.approve: 0,
        RiskDecision.review: 1,
        RiskDecision.decline: 2,
    }
    return triggered if order[triggered] > order[current] else current
