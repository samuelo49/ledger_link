from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class RiskDecision(str, enum.Enum):
    approve = "approve"
    review = "review"
    decline = "decline"


class RiskRuleType(str, enum.Enum):
    amount_threshold = "amount_threshold"
    country_mismatch = "country_mismatch"
    blocklist_country = "blocklist_country"
    email_domain_block = "email_domain_block"


class RiskRule(Base):
    __tablename__ = "risk_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    event_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    rule_type: Mapped[RiskRuleType] = mapped_column(SqlEnum(RiskRuleType), nullable=False)
    action: Mapped[RiskDecision] = mapped_column(SqlEnum(RiskDecision), nullable=False)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    weight: Mapped[float] = mapped_column(default=1.0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
