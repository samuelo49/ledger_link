from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_session
from ..models import RiskEvaluation, RiskRule
from ..risk_engine import EvaluationContext, RiskEngine
from ..schemas import (
    RiskEvaluationRequest,
    RiskEvaluationResponse,
    RiskRuleResponse,
    TriggeredRuleSchema,
)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/rules", response_model=list[RiskRuleResponse])
async def list_rules(session: SessionDep) -> list[RiskRule]:
    result = await session.scalars(select(RiskRule).order_by(RiskRule.id))
    return list(result)


@router.get("/evaluations/{evaluation_id}", response_model=RiskEvaluationResponse)
async def get_evaluation(evaluation_id: UUID, session: SessionDep) -> RiskEvaluation:
    evaluation = await session.get(RiskEvaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return RiskEvaluationResponse.model_validate(evaluation)


@router.post("/evaluations", response_model=RiskEvaluationResponse, status_code=status.HTTP_201_CREATED)
async def evaluate(payload: RiskEvaluationRequest, session: SessionDep) -> RiskEvaluationResponse:
    rules_stmt = (
        select(RiskRule)
        .where(
            RiskRule.enabled.is_(True),
            RiskRule.event_types.contains([payload.event_type]),
        )
        .order_by(RiskRule.id)
    )
    rules = list(await session.scalars(rules_stmt))
    engine = RiskEngine(rules)
    ctx = EvaluationContext(
        event_type=payload.event_type,
        subject_id=payload.subject_id,
        user_id=payload.user_id,
        amount=Decimal(payload.amount),
        currency=payload.currency.upper(),
        metadata=payload.metadata or {},
    )
    result = engine.evaluate(ctx)

    evaluation = RiskEvaluation(
        event_type=ctx.event_type,
        subject_id=ctx.subject_id,
        user_id=ctx.user_id,
        amount=ctx.amount,
        currency=ctx.currency,
        decision=result.decision,
        risk_score=result.risk_score,
        triggered_rules=[asdict(rule) for rule in result.triggered_rules],
        metadata=ctx.metadata,
    )
    session.add(evaluation)
    await session.commit()
    await session.refresh(evaluation)
    response = RiskEvaluationResponse(
        id=evaluation.id,
        decision=evaluation.decision,
        risk_score=evaluation.risk_score,
        triggered_rules=[TriggeredRuleSchema(**asdict(rule)) for rule in result.triggered_rules],
        created_at=evaluation.created_at,
    )
    return response
