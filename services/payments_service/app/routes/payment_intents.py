from __future__ import annotations

from typing import Annotated
from time import perf_counter
import asyncio

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.payment_intent import PaymentIntent, PaymentIntentStatus
from ..schemas.payment_intent import (
    PaymentIntentCreate,
    PaymentIntentResponse,
    PaymentIntentConfirmRequest,
)
from ..dependencies import get_current_user_id, get_session
from ..metrics import (
    payment_intent_created_total,
    payment_intent_confirmed_total,
    payment_intent_wallet_debit_failures_total,
    wallet_debit_latency_seconds,
    payment_intent_risk_decision_total,
)
from ..settings import payments_settings

router = APIRouter(prefix="/payments/intents", tags=["payment-intents"])


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
        select(PaymentIntent)
        .where(PaymentIntent.id == intent_id, 
               PaymentIntent.user_id == current_user_id
               )
    )
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")
    if intent.status != PaymentIntentStatus.pending.value:
        # Idempotent confirms return the current status (confirmed/review/declined)
        return PaymentIntentResponse.model_validate(intent)

    # Debit wallet via wallet service using same bearer token for ownership enforcement
    settings = payments_settings()
    auth_header = request.headers.get("authorization")

    risk_result = await _evaluate_risk(intent, request, settings)
    decision = risk_result.get("decision")
    if decision == "decline":
        intent.status = PaymentIntentStatus.declined.value
        session.add(intent)
        await session.commit()
        await session.refresh(intent)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Payment declined by risk engine")
    if decision == "review":
        intent.status = PaymentIntentStatus.review.value
        session.add(intent)
        await session.commit()
        await session.refresh(intent)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment pending manual review")

    hold_id = await _ensure_hold(intent, auth_header, settings, session)
    await _capture_hold(intent, hold_id, auth_header, settings)

    intent.status = PaymentIntentStatus.confirmed.value
    session.add(intent)
    await session.commit()
    await session.refresh(intent)
    payment_intent_confirmed_total.labels(currency=intent.currency).inc()
    return PaymentIntentResponse.model_validate(intent)


@router.post("/{intent_id}/cancel", response_model=PaymentIntentResponse)
async def cancel_intent(
    intent_id: int,
    request: Request,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> PaymentIntentResponse:
    intent = await session.scalar(
        select(PaymentIntent).where(PaymentIntent.id == intent_id, PaymentIntent.user_id == current_user_id)
    )
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")
    if intent.status == PaymentIntentStatus.canceled.value:
        return PaymentIntentResponse.model_validate(intent)
    if intent.status not in {PaymentIntentStatus.pending.value, PaymentIntentStatus.review.value}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Intent can no longer be canceled")

    settings = payments_settings()
    auth_header = request.headers.get("authorization")
    if intent.hold_id:
        await _release_hold(intent, intent.hold_id, auth_header, settings)

    intent.status = PaymentIntentStatus.canceled.value
    session.add(intent)
    await session.commit()
    await session.refresh(intent)
    return PaymentIntentResponse.model_validate(intent)
async def _evaluate_risk(intent: PaymentIntent, request: Request, settings) -> dict:
    metadata = {
        "wallet_id": intent.wallet_id,
        "client_ip": request.client.host if request.client else None,
        "ip_country": request.headers.get("x-risk-ip-country"),
        "user_country": request.headers.get("x-user-country"),
        "email_domain": request.headers.get("x-user-email-domain"),
        "user_agent": request.headers.get("user-agent"),
    }
    risk_payload = {
        "event_type": "payment_intent_confirm",
        "subject_id": str(intent.id),
        "user_id": str(intent.user_id),
        "amount": str(intent.amount),
        "currency": intent.currency,
        "metadata": {k: v for k, v in metadata.items() if v},
    }
    risk_url = f"{settings.risk_base_url}/evaluations"
    timeout = httpx.Timeout(settings.risk_timeout_seconds, read=settings.risk_timeout_seconds)
    headers = {"Idempotency-Key": f"pi-risk-{intent.id}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(risk_url, json=risk_payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Risk evaluation timed out",
        ) from exc
    except httpx.HTTPError as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Risk service unreachable",
        ) from exc
    if response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Risk service unavailable",
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Risk evaluation failed",
        )
    data = response.json()
    decision = data.get("decision")
    if decision:
        payment_intent_risk_decision_total.labels(decision=decision).inc()
    return data


async def _post_wallet_with_retry(
    url: str,
    payload: dict,
    auth_header: str | None,
    settings,
    operation: str,
) -> httpx.Response:
    timeout = httpx.Timeout(settings.wallet_timeout_seconds, read=settings.wallet_timeout_seconds)
    headers = {"Authorization": auth_header} if auth_header else {}
    last_reason = "unknown"
    for attempt in range(1, settings.wallet_retry_attempts + 1):
        start = perf_counter()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            last_reason = "timeout"
            payment_intent_wallet_debit_failures_total.labels(reason=f"{operation}_timeout").inc()
        except httpx.HTTPError:
            last_reason = "network"
            payment_intent_wallet_debit_failures_total.labels(reason=f"{operation}_network").inc()
        else:
            duration = perf_counter() - start
            wallet_debit_latency_seconds.observe(duration)
            if response.status_code < 400:
                return response
            last_reason = f"status_{response.status_code}"
            payment_intent_wallet_debit_failures_total.labels(reason=f"{operation}_{response.status_code}").inc()

        if attempt < settings.wallet_retry_attempts:
            await asyncio.sleep(settings.wallet_retry_backoff_seconds * attempt)

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"Wallet {operation} failed ({last_reason})",
    )


async def _ensure_hold(
    intent: PaymentIntent,
    auth_header: str | None,
    settings,
    session: AsyncSession,
) -> int:
    if intent.hold_id:
        return intent.hold_id

    create_url = f"http://wallet-service:8000/api/v1/wallets/{intent.wallet_id}/holds"
    payload = {
        "amount": str(intent.amount),
        "idempotency_key": f"pi-hold-{intent.id}",
        "reference": f"pi-{intent.id}",
        "details": {"payment_intent_id": intent.id, "type": "payment_hold"},
    }
    response = await _post_wallet_with_retry(create_url, payload, auth_header, settings, operation="hold_create")
    data = response.json()
    hold_id = data.get("id")
    if hold_id is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Wallet hold response missing id")

    intent.hold_id = hold_id
    session.add(intent)
    await session.commit()
    await session.refresh(intent)
    return hold_id


async def _capture_hold(intent: PaymentIntent, hold_id: int, auth_header: str | None, settings) -> None:
    capture_url = f"http://wallet-service:8000/api/v1/wallets/{intent.wallet_id}/holds/{hold_id}/capture"
    payload = {"idempotency_key": f"pi-hold-capture-{intent.id}"}
    response = await _post_wallet_with_retry(capture_url, payload, auth_header, settings, operation="hold_capture")
    data = response.json()
    status_value = data.get("status")
    if status_value not in {"captured", "released"}:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected wallet hold state ({status_value})",
        )


async def _release_hold(intent: PaymentIntent, hold_id: int, auth_header: str | None, settings) -> None:
    release_url = f"http://wallet-service:8000/api/v1/wallets/{intent.wallet_id}/holds/{hold_id}/release"
    payload = {"idempotency_key": f"pi-hold-release-{intent.id}"}
    response = await _post_wallet_with_retry(release_url, payload, auth_header, settings, operation="hold_release")
    data = response.json()
    status_value = data.get("status")
    if status_value not in {"released"}:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unexpected wallet hold release state ({status_value})",
        )
