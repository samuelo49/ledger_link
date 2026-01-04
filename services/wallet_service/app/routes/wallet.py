from __future__ import annotations

from decimal import Decimal
from time import perf_counter
from typing import Annotated, Sequence

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from services.wallet_service.app.models import (
    Wallet,
    LedgerEntry,
    EntryType,
    Hold,
    HoldStatus,
    Transfer,
    TransferStatus,
    OutboxEvent,
)
from services.wallet_service.app.schemas import (
    WalletCreate,
    WalletResponse,
    MoneyChangeRequest,
    BalanceResponse,
    TransferRequest,
    TransferResponse,
    TransferRecord,
    HoldCreateRequest,
    HoldResponse,
    HoldActionRequest,
    LedgerEntryItem,
    StatementResponse,
    ReconciliationResponse,
)
from services.wallet_service.app.dependencies import get_current_user_id, get_session
from services.wallet_service.app.metrics import (
    wallet_credit_total,
    wallet_debit_total,
    wallet_idempotency_replay_total,
    wallet_insufficient_funds_total,
    wallet_transfer_created_total,
    wallet_transfer_completed_total,
    wallet_transfer_failed_total,
    wallet_transfer_idempotent_total,
    wallet_transfer_latency_seconds,
)
from services.wallet_service.app.settings import wallet_settings


router = APIRouter()


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def _record_outbox_event(session: AsyncSession, event_type: str, payload: dict) -> None:
    event = OutboxEvent(event_type=event_type, payload=payload)
    session.add(event)


def _wallet_response(wallet: Wallet) -> WalletResponse:
    return WalletResponse(
        id=wallet.id,
        owner_user_id=wallet.owner_user_id,
        currency=wallet.currency,
        status=wallet.status,
        balance=wallet.balance,
    )


def _hold_response(hold: Hold) -> HoldResponse:
    return HoldResponse(
        id=hold.id,
        wallet_id=hold.wallet_id,
        amount=hold.amount,
        status=hold.status,
        reference=hold.reference,
        created_at=hold.created_at,
        updated_at=hold.updated_at,
    )


async def _get_hold(
    session: AsyncSession,
    wallet_id: int,
    hold_id: int,
    current_user_id: int,
    for_update: bool = False,
) -> Hold:
    stmt = (
        select(Hold)
        .join(Wallet, Wallet.id == Hold.wallet_id)
        .where(Hold.id == hold_id, Hold.wallet_id == wallet_id, Wallet.owner_user_id == current_user_id)
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    hold = result.scalar_one_or_none()
    if hold is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hold not found")
    return hold


def _extract_risk_metadata(request: Request) -> dict[str, str]:
    return {
        "ip_country": request.headers.get("x-risk-ip-country", ""),
        "user_country": request.headers.get("x-user-country", ""),
        "client_ip": request.client.host if request.client else "",
        "user_agent": request.headers.get("user-agent", ""),
    }


async def _enforce_wallet_risk(
    wallet: Wallet,
    amount: Decimal,
    current_user_id: int,
    risk_metadata: dict | None,
) -> None:
    settings = wallet_settings()
    if not settings.risk_checks_enabled:
        return
    payload = {
        "event_type": "wallet_transaction",
        "subject_id": str(wallet.id),
        "user_id": str(current_user_id),
        "amount": str(amount),
        "currency": wallet.currency,
        "metadata": {
            "wallet_owner": wallet.owner_user_id,
            "transaction_type": "debit",
            **(risk_metadata or {}),
        },
    }
    risk_url = f"{settings.risk_base_url}/evaluations"
    timeout = httpx.Timeout(5.0, read=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(risk_url, json=payload)
    if response.status_code >= 500:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Risk service unavailable")
    if response.status_code >= 400:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wallet risk evaluation failed")
    decision = response.json().get("decision")
    if decision == "decline":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Wallet transaction declined by risk engine")
    if decision == "review":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Wallet transaction pending risk review")


@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(
    payload: WalletCreate,
    session: SessionDep,
    response: Response,
    current_user_id: int = Depends(get_current_user_id),
) -> WalletResponse:
    if not payload.allow_additional:
        # Enforce one wallet per (owner, currency) unless caller explicitly requests another
        existing = await session.execute(
            select(Wallet).where(Wallet.owner_user_id == current_user_id, Wallet.currency == payload.currency)
        )
        if (row := existing.scalar_one_or_none()) is not None:
            response.status_code = status.HTTP_200_OK
            return _wallet_response(row)

    wallet = Wallet(owner_user_id=current_user_id, currency=payload.currency)
    session.add(wallet)
    await session.commit()
    return _wallet_response(wallet)


async def _apply_money_change(
    session: AsyncSession,
    wallet_id: int,
    kind: EntryType,
    amount: Decimal,
    idempotency_key: str | None,
    details: dict | None,
    current_user_id: int,
    risk_metadata: dict | None = None,
) -> tuple[Wallet, LedgerEntry]:
    # Lock the wallet row to prevent races
    result = await session.execute(
        select(Wallet).where(Wallet.id == wallet_id, Wallet.owner_user_id == current_user_id).with_for_update()
    )
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or not owned by user")

    # Idempotency: if key provided, check existing entry
    if idempotency_key:
        existing = await session.execute(
            select(LedgerEntry).where(
                LedgerEntry.wallet_id == wallet_id,
                LedgerEntry.idempotency_key == idempotency_key,
            ).limit(1)
        )
        if (entry := existing.scalar_one_or_none()) is not None:
            # If an entry exists, consider operation idempotent and return current wallet state
            wallet_idempotency_replay_total.labels(currency=wallet.currency, type=kind.value).inc()
            return wallet, entry  # entry retrieved below but to satisfy type we set placeholder

    if kind == EntryType.debit:
        await _enforce_wallet_risk(wallet, amount, current_user_id, risk_metadata)

    if kind == EntryType.debit:
        if wallet.balance < amount:
            wallet_insufficient_funds_total.labels(currency=wallet.currency).inc()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Insufficient funds")
        wallet.balance = wallet.balance - amount
    else:
        wallet.balance = wallet.balance + amount

    entry = LedgerEntry(
        wallet_id=wallet.id,
        type=kind.value,
        amount=amount,
        idempotency_key=idempotency_key,
        details=details or None,
    )
    session.add(entry)
    await session.flush()
    if kind == EntryType.debit:
        wallet_debit_total.labels(currency=wallet.currency).inc()
    else:
        wallet_credit_total.labels(currency=wallet.currency).inc()
    return wallet, entry


async def _lock_wallets(session: AsyncSession, wallet_ids: list[int], current_user_id: int) -> dict[int, Wallet]:
    locked: dict[int, Wallet] = {}
    for wid in sorted(wallet_ids):
        result = await session.execute(
            select(Wallet).where(Wallet.id == wid, Wallet.owner_user_id == current_user_id).with_for_update()
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or not owned by user")
        locked[wid] = wallet
    return locked


@router.post("/{wallet_id}/credit", response_model=WalletResponse)
async def credit_wallet(wallet_id: int, payload: MoneyChangeRequest, request: Request, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> WalletResponse:
    async with session.begin():
        wallet, _ = await _apply_money_change(
            session,
            wallet_id,
            EntryType.credit,
            payload.amount,
            payload.idempotency_key,
            payload.details,
            current_user_id,
            _extract_risk_metadata(request),
        )
    return _wallet_response(wallet)


@router.post("/{wallet_id}/debit", response_model=WalletResponse)
async def debit_wallet(wallet_id: int, payload: MoneyChangeRequest, request: Request, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> WalletResponse:
    async with session.begin():
        wallet, _ = await _apply_money_change(
            session,
            wallet_id,
            EntryType.debit,
            payload.amount,
            payload.idempotency_key,
            payload.details,
            current_user_id,
            _extract_risk_metadata(request),
        )
    return _wallet_response(wallet)


@router.get("/{wallet_id}/balance", response_model=BalanceResponse)
async def get_balance(wallet_id: int, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> BalanceResponse:
    result = await session.execute(select(Wallet).where(Wallet.id == wallet_id, Wallet.owner_user_id == current_user_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or not owned by user")
    return BalanceResponse(id=wallet.id, currency=wallet.currency, balance=wallet.balance)


def _entry_item(entry: LedgerEntry) -> LedgerEntryItem:
    return LedgerEntryItem(
        id=entry.id,
        type=EntryType(entry.type),
        amount=entry.amount,
        details=entry.details,
        created_at=entry.created_at,
    )


def _transfer_record(transfer: Transfer) -> TransferRecord:
    return TransferRecord(
        id=transfer.id,
        status=TransferStatus(transfer.status),
        amount=transfer.amount,
        currency=transfer.currency,
        idempotency_key=transfer.idempotency_key,
        failure_reason=transfer.failure_reason,
        external_reference=transfer.external_reference,
        created_at=transfer.created_at,
        updated_at=transfer.updated_at,
    )


def _transfer_payload(transfer: Transfer) -> dict:
    return {
        "transfer_id": transfer.id,
        "user_id": transfer.user_id,
        "source_wallet_id": transfer.source_wallet_id,
        "target_wallet_id": transfer.target_wallet_id,
        "status": transfer.status,
        "amount": str(transfer.amount),
        "currency": transfer.currency,
        "idempotency_key": transfer.idempotency_key,
        "external_reference": transfer.external_reference,
    }


@router.post("/{wallet_id}/transfers", response_model=TransferResponse, status_code=status.HTTP_201_CREATED)
async def transfer_between_wallets(
    wallet_id: int,
    payload: TransferRequest,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> TransferResponse:
    if wallet_id == payload.target_wallet_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source and target wallet must differ")

    transfer_start = perf_counter()
    failure_exc: HTTPException | None = None
    async with session.begin():
        existing_transfer = await session.scalar(
            select(Transfer).where(Transfer.idempotency_key == payload.idempotency_key)
        )
        if existing_transfer is not None:
            if existing_transfer.user_id != current_user_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Transfer belongs to another user")
            wallet_transfer_idempotent_total.labels(currency=existing_transfer.currency).inc()
            locked = await _lock_wallets(
                session,
                [existing_transfer.source_wallet_id, existing_transfer.target_wallet_id],
                current_user_id,
            )
            if existing_transfer.status == TransferStatus.failed.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=existing_transfer.failure_reason or "Transfer previously failed",
                )
            if existing_transfer.status == TransferStatus.pending.value:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transfer is still processing")
            transfer_response = TransferResponse(
                transfer=_transfer_record(existing_transfer),
                source_wallet=_wallet_response(locked[existing_transfer.source_wallet_id]),
                target_wallet=_wallet_response(locked[existing_transfer.target_wallet_id]),
            )
            return transfer_response

        locked = await _lock_wallets(session, [wallet_id, payload.target_wallet_id], current_user_id)
        source = locked[wallet_id]
        target = locked[payload.target_wallet_id]

        if source.currency != target.currency or payload.currency != source.currency:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Currency mismatch")

        transfer = Transfer(
            user_id=current_user_id,
            source_wallet_id=source.id,
            target_wallet_id=target.id,
            amount=payload.amount,
            currency=source.currency,
            idempotency_key=payload.idempotency_key,
            external_reference=payload.external_reference,
        )
        session.add(transfer)
        await session.flush()
        wallet_transfer_created_total.labels(currency=transfer.currency).inc()
        _record_outbox_event(session, "wallet.transfer.created", _transfer_payload(transfer))

        transfer_details = {
            "type": "transfer",
            "transfer_id": transfer.id,
            "target_wallet_id": target.id,
            "description": payload.description,
        }
        reverse_details = {
            "type": "transfer",
            "transfer_id": transfer.id,
            "source_wallet_id": source.id,
            "description": payload.description,
        }

        debit_key = f"wallet-transfer-debit-{transfer.id}"
        credit_key = f"wallet-transfer-credit-{transfer.id}"

        try:
            source, debit_entry = await _apply_money_change(
                session,
                source.id,
                EntryType.debit,
                payload.amount,
                debit_key,
                transfer_details,
                current_user_id,
                risk_metadata=None,
            )
            target, credit_entry = await _apply_money_change(
                session,
                target.id,
                EntryType.credit,
                payload.amount,
                credit_key,
                reverse_details,
                current_user_id,
                risk_metadata=None,
            )
        except HTTPException as exc:
            transfer.status = TransferStatus.failed.value
            transfer.failure_reason = str(exc.detail) if exc.detail else "Transfer failed"
            wallet_transfer_failed_total.labels(
                currency=transfer.currency,
                reason="insufficient_funds" if exc.status_code == status.HTTP_409_CONFLICT else "validation_error",
            ).inc()
            _record_outbox_event(session, "wallet.transfer.failed", _transfer_payload(transfer))
            failure_exc = exc
        else:
            transfer.status = TransferStatus.completed.value
            transfer.ledger_debit_entry_id = debit_entry.id
            transfer.ledger_credit_entry_id = credit_entry.id
            wallet_transfer_completed_total.labels(currency=transfer.currency).inc()
            wallet_transfer_latency_seconds.observe(perf_counter() - transfer_start)
            _record_outbox_event(session, "wallet.transfer.completed", _transfer_payload(transfer))
            response = TransferResponse(
                transfer=_transfer_record(transfer),
                source_wallet=_wallet_response(source),
                target_wallet=_wallet_response(target),
            )

    if failure_exc:
        raise failure_exc
    return response


@router.post("/{wallet_id}/holds", response_model=HoldResponse, status_code=status.HTTP_201_CREATED)
async def create_hold(
    wallet_id: int,
    payload: HoldCreateRequest,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> HoldResponse:
    async with session.begin():
        existing = await session.execute(
            select(Hold)
            .where(Hold.wallet_id == wallet_id, Hold.idempotency_key == payload.idempotency_key)
            .with_for_update()
        )
        if (hold := existing.scalar_one_or_none()) is not None:
            return _hold_response(hold)

        wallet, entry = await _apply_money_change(
            session,
            wallet_id,
            EntryType.debit,
            payload.amount,
            payload.idempotency_key,
            {"type": "hold", "reference": payload.reference},
            current_user_id,
        )
        hold = Hold(
            wallet_id=wallet.id,
            amount=payload.amount,
            status=HoldStatus.active.value,
            idempotency_key=payload.idempotency_key,
            reference=payload.reference,
            details=payload.details,
            ledger_entry_id=entry.id,
        )
        session.add(hold)
        await session.flush()
        await session.refresh(hold)
        return _hold_response(hold)


@router.post("/{wallet_id}/holds/{hold_id}/release", response_model=HoldResponse)
async def release_hold(
    wallet_id: int,
    hold_id: int,
    payload: HoldActionRequest,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> HoldResponse:
    async with session.begin():
        hold = await _get_hold(session, wallet_id, hold_id, current_user_id, for_update=True)
        if hold.status == HoldStatus.captured.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hold already captured")
        if hold.status == HoldStatus.released.value:
            return _hold_response(hold)

        idem = payload.idempotency_key or f"hold-release-{hold.id}"
        await _apply_money_change(
            session,
            wallet_id,
            EntryType.credit,
            hold.amount,
            idem,
            {"type": "hold_release", "hold_id": hold.id},
            current_user_id,
        )
        hold.status = HoldStatus.released.value
        session.add(hold)
        await session.flush()
        await session.refresh(hold)
        return _hold_response(hold)


@router.post("/{wallet_id}/holds/{hold_id}/capture", response_model=HoldResponse)
async def capture_hold(
    wallet_id: int,
    hold_id: int,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> HoldResponse:
    async with session.begin():
        hold = await _get_hold(session, wallet_id, hold_id, current_user_id, for_update=True)
        if hold.status == HoldStatus.released.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Hold already released")
        if hold.status == HoldStatus.captured.value:
            return _hold_response(hold)
        hold.status = HoldStatus.captured.value
        session.add(hold)
        await session.flush()
        await session.refresh(hold)
        return _hold_response(hold)


@router.get("/{wallet_id}/statements", response_model=StatementResponse)
async def list_statements(
    wallet_id: int,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
    limit: int = 50,
    cursor: int | None = None,
) -> StatementResponse:
    limit = max(1, min(limit, 200))
    wallet_result = await session.execute(
        select(Wallet.id).where(Wallet.id == wallet_id, Wallet.owner_user_id == current_user_id)
    )
    if wallet_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or not owned by user")

    stmt = select(LedgerEntry).where(LedgerEntry.wallet_id == wallet_id).order_by(LedgerEntry.id.desc()).limit(limit)
    if cursor:
        stmt = stmt.where(LedgerEntry.id < cursor)
    result = await session.execute(
        stmt.join(Wallet, Wallet.id == LedgerEntry.wallet_id).where(Wallet.owner_user_id == current_user_id)
    )
    entries: Sequence[LedgerEntry] = result.scalars().all()
    next_cursor = entries[-1].id if entries and len(entries) == limit else None
    return StatementResponse(wallet_id=wallet_id, entries=[_entry_item(e) for e in entries], next_cursor=next_cursor)


@router.get("/{wallet_id}/reconciliation", response_model=ReconciliationResponse)
async def reconcile_wallet(
    wallet_id: int,
    session: SessionDep,
    current_user_id: int = Depends(get_current_user_id),
) -> ReconciliationResponse:
    wallet_result = await session.execute(
        select(Wallet).where(Wallet.id == wallet_id, Wallet.owner_user_id == current_user_id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or not owned by user")

    ledger_stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (LedgerEntry.type == EntryType.credit.value, LedgerEntry.amount),
                    else_=-LedgerEntry.amount,
                )
            ),
            0,
        ).label("ledger_balance"),
        func.count(LedgerEntry.id).label("entry_count"),
    ).where(LedgerEntry.wallet_id == wallet_id)
    agg = await session.execute(ledger_stmt)
    ledger_balance, entry_count = agg.one()
    delta = ledger_balance - wallet.balance
    status_text = "balanced" if delta == 0 else "drift_detected"
    return ReconciliationResponse(
        wallet_id=wallet_id,
        stored_balance=wallet.balance,
        ledger_balance=ledger_balance,
        delta=delta,
        entry_count=entry_count,
        status=status_text,
    )
