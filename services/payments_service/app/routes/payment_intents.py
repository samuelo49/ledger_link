from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from ..db.session import async_session_factory
from ..models.payment_intent import PaymentIntent, PaymentIntentStatus
from ..schemas.payment_intent import (
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentIntentConfirmRequest,
)
from ..dependencies import get_current_user_id
from ..metrics import payment_intent_created_total, payment_intent_confirmed_total
from ..settings import payments_settings

router = APIRouter(prefix="/payments/intents", tags=["payment-intents"])


async def get_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=PaymentIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_intent(
    payload: PaymentIntentCreate,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> PaymentIntentResponse:
    intent = PaymentIntent(
        user_id=current_user_id,
        wallet_id=payload.wallet_id,
        amount=payload.amount,
        currency=payload.currency,
        status=PaymentIntentStatus.pending.value,
    )
    session.add(intent)
    await session.commit()
    await session.refresh(intent)
    payment_intent_created_total.labels(currency=intent.currency).inc()
    return PaymentIntentResponse.model_validate(intent)


@router.get("/{intent_id}", response_model=PaymentIntentResponse)
async def get_intent(intent_id: int, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> PaymentIntentResponse:
    intent = await session.scalar(
        select(PaymentIntent).where(PaymentIntent.id == intent_id, PaymentIntent.user_id == current_user_id)
    )
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")
    return PaymentIntentResponse.model_validate(intent)


@router.post("/{intent_id}/confirm", response_model=PaymentIntentResponse)
async def confirm_intent(
    intent_id: int,
    _payload: PaymentIntentConfirmRequest,  # reserved for future fields
    request: Request,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> PaymentIntentResponse:
    intent = await session.scalar(
        select(PaymentIntent).where(PaymentIntent.id == intent_id, PaymentIntent.user_id == current_user_id)
    )
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")
    if intent.status != PaymentIntentStatus.pending.value:
        return PaymentIntentResponse.model_validate(intent)  # idempotent confirm

    # Debit wallet via wallet service using same bearer token for ownership enforcement
    settings = payments_settings()
    auth_header = request.headers.get("authorization")
    wallet_debit_url = f"http://wallet-service:8000/api/v1/wallets/{intent.wallet_id}/debit"
    debit_payload = {
        "amount": str(intent.amount),
        "idempotency_key": f"pi-confirm-{intent.id}",
        "details": {"payment_intent_id": intent.id},
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=20.0)) as client:
        upstream = await client.post(wallet_debit_url, json=debit_payload, headers={"Authorization": auth_header})
    if upstream.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wallet debit failed")

    intent.status = PaymentIntentStatus.confirmed.value
    session.add(intent)
    await session.commit()
    await session.refresh(intent)
    payment_intent_confirmed_total.labels(currency=intent.currency).inc()
    return PaymentIntentResponse.model_validate(intent)
