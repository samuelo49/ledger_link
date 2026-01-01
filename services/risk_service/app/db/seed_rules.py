from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RiskRule, RiskDecision, RiskRuleType


DEFAULT_RULES = [
    {
        "name": "high_value_payment",
        "description": "Escalate high value payment confirmations for review.",
        "event_types": ["payment_intent_confirm"],
        "rule_type": RiskRuleType.amount_threshold,
        "action": RiskDecision.review,
        "weight": 2.0,
        "config": {
            "thresholds": {
                "USD": "5000",
                "EUR": "4500",
                "default": "4000",
            }
        },
    },
    {
        "name": "blocked_ip_country",
        "description": "Block traffic originating from embargoed countries.",
        "event_types": ["payment_intent_confirm", "wallet_transaction"],
        "rule_type": RiskRuleType.blocklist_country,
        "action": RiskDecision.decline,
        "weight": 5.0,
        "config": {"blocked": ["KP", "SY", "IR"]},
    },
    {
        "name": "country_mismatch_review",
        "description": "Require review when IP country differs from the known user country.",
        "event_types": ["payment_intent_confirm", "wallet_transaction"],
        "rule_type": RiskRuleType.country_mismatch,
        "action": RiskDecision.review,
        "weight": 1.0,
        "config": {},
    },
    {
        "name": "disposable_email_block",
        "description": "Block attempts from disposable email domains.",
        "event_types": ["payment_intent_confirm"],
        "rule_type": RiskRuleType.email_domain_block,
        "action": RiskDecision.decline,
        "weight": 3.0,
        "config": {"domains": ["mailinator.com", "tempmail.com"]},
    },
]


async def seed_default_rules(session: AsyncSession) -> None:
    existing = await session.scalars(
        select(RiskRule.name).where(RiskRule.name.in_([rule["name"] for rule in DEFAULT_RULES]))
    )
    existing_names = set(existing)

    created = 0
    for rule in DEFAULT_RULES:
        if rule["name"] in existing_names:
            continue
        session.add(RiskRule(**rule))
        created += 1

    if created:
        await session.commit()
    else:
        await session.rollback()
