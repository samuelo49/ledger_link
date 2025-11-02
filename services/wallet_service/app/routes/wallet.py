from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from services.wallet_service.app.db.session import async_session_factory
from services.wallet_service.app.models import Wallet, LedgerEntry, EntryType
from services.wallet_service.app.schemas import (
    WalletCreate,
    WalletResponse,
    MoneyChangeRequest,
    BalanceResponse,
)
from services.wallet_service.app.dependencies import get_current_user_id
from services.wallet_service.app.metrics import (
    wallet_credit_total,
    wallet_debit_total,
    wallet_idempotency_replay_total,
    wallet_insufficient_funds_total,
)


router = APIRouter()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/", response_model=WalletResponse, status_code=status.HTTP_201_CREATED)
async def create_wallet(payload: WalletCreate, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> WalletResponse:
    # Enforce one wallet per (owner, currency)
    existing = await session.execute(
        select(Wallet).where(Wallet.owner_user_id == current_user_id, Wallet.currency == payload.currency)
    )
    if (row := existing.scalar_one_or_none()) is not None:
        # Idempotent create: return existing
        return WalletResponse(
            id=row.id,
            owner_user_id=row.owner_user_id,
            currency=row.currency,
            status=row.status,
            balance=row.balance,
        )

    wallet = Wallet(owner_user_id=current_user_id, currency=payload.currency)
    session.add(wallet)
    await session.commit()
    await session.refresh(wallet)
    return WalletResponse(
        id=wallet.id,
        owner_user_id=wallet.owner_user_id,
        currency=wallet.currency,
        status=wallet.status,
        balance=wallet.balance,
    )


async def _apply_money_change(
    session: AsyncSession,
    wallet_id: int,
    kind: EntryType,
    amount: Decimal,
    idempotency_key: str | None,
    metadata: dict | None,
    current_user_id: int,
) -> Wallet:
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
            return wallet

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
        metadata=metadata or None,
    )
    session.add(entry)
    await session.flush()
    await session.commit()
    await session.refresh(wallet)
    if kind == EntryType.debit:
        wallet_debit_total.labels(currency=wallet.currency).inc()
    else:
        wallet_credit_total.labels(currency=wallet.currency).inc()
    return wallet


@router.post("/{wallet_id}/credit", response_model=WalletResponse)
async def credit_wallet(wallet_id: int, payload: MoneyChangeRequest, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> WalletResponse:
    async with session.begin():
        wallet = await _apply_money_change(
            session,
            wallet_id,
            EntryType.credit,
            payload.amount,
            payload.idempotency_key,
            payload.metadata,
            current_user_id,
        )
    return WalletResponse(
        id=wallet.id,
        owner_user_id=wallet.owner_user_id,
        currency=wallet.currency,
        status=wallet.status,
        balance=wallet.balance,
    )


@router.post("/{wallet_id}/debit", response_model=WalletResponse)
async def debit_wallet(wallet_id: int, payload: MoneyChangeRequest, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> WalletResponse:
    async with session.begin():
        wallet = await _apply_money_change(
            session,
            wallet_id,
            EntryType.debit,
            payload.amount,
            payload.idempotency_key,
            payload.metadata,
            current_user_id,
        )
    return WalletResponse(
        id=wallet.id,
        owner_user_id=wallet.owner_user_id,
        currency=wallet.currency,
        status=wallet.status,
        balance=wallet.balance,
    )


@router.get("/{wallet_id}/balance", response_model=BalanceResponse)
async def get_balance(wallet_id: int, session: SessionDep, current_user_id: int = Depends(get_current_user_id)) -> BalanceResponse:
    result = await session.execute(select(Wallet).where(Wallet.id == wallet_id, Wallet.owner_user_id == current_user_id))
    wallet = result.scalar_one_or_none()
    if wallet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found or not owned by user")
    return BalanceResponse(id=wallet.id, currency=wallet.currency, balance=wallet.balance)
