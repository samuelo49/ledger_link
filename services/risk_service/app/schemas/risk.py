from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ..models import RiskDecision


class TriggeredRuleSchema(BaseModel):
    rule_id: int
    name: str
    action: RiskDecision
    reason: str
    weight: float


class RiskEvaluationRequest(BaseModel):
    event_type: str = Field(..., description="Domain event type, e.g. payment_intent_confirm")
    subject_id: str = Field(..., description="Identifier for the entity under evaluation")
    user_id: str
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RiskEvaluationResponse(BaseModel):
    id: UUID
    decision: RiskDecision
    risk_score: float
    triggered_rules: list[TriggeredRuleSchema]
    created_at: datetime


class RiskRuleResponse(BaseModel):
    id: int
    name: str
    description: str
    event_types: list[str]
    rule_type: str
    action: RiskDecision
    weight: float
    enabled: bool

    class Config:
        from_attributes = True
