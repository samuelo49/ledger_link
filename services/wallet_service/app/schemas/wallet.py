from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic import ConfigDict

from services.wallet_service.app.models import EntryType


class WalletCreate(BaseModel):
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code, e.g. USD")
    allow_additional: bool = Field(
        False,
        description="Set true to create a new wallet even if one already exists for this currency/owner",
    )


class WalletResponse(BaseModel):
    id: int
    owner_user_id: int
    currency: str
    status: str
    balance: Decimal


class MoneyChangeRequest(BaseModel):
    """Request body for credit/debit operations.

    Accepts either 'details' (preferred) or legacy 'metadata' key in inbound JSON
    via aliasing to support a gradual migration away from the reserved ORM name.
    """

    amount: Decimal = Field(..., gt=0)
    idempotency_key: str | None = Field(None, max_length=64)
    # Alias allows clients to continue sending 'metadata'; internally we use 'details'.
    details: dict | None = Field(
        None,
        alias="metadata",
        description="Optional metadata payload persisted with the ledger entry (alias: metadata)",
    )

    # Pydantic v2 configuration enabling population by field name or alias.
    model_config = ConfigDict(populate_by_name=True)


class BalanceResponse(BaseModel):
    id: int
    currency: str
    balance: Decimal


class TransferRequest(BaseModel):
    target_wallet_id: int
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    idempotency_key: str = Field(..., max_length=64)
    description: str | None = None


class TransferResponse(BaseModel):
    source_wallet: WalletResponse
    target_wallet: WalletResponse


class HoldCreateRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    idempotency_key: str = Field(..., max_length=64)
    reference: str | None = Field(None, max_length=64)
    details: dict | None = Field(None, alias="metadata")

    model_config = ConfigDict(populate_by_name=True)


class HoldActionRequest(BaseModel):
    idempotency_key: str | None = Field(None, max_length=64)


class HoldResponse(BaseModel):
    id: int
    wallet_id: int
    amount: Decimal
    status: str
    reference: str | None
    created_at: datetime
    updated_at: datetime


class LedgerEntryItem(BaseModel):
    id: int
    type: EntryType
    amount: Decimal
    details: dict | None
    created_at: datetime


class StatementResponse(BaseModel):
    wallet_id: int
    entries: list[LedgerEntryItem]
    next_cursor: int | None = None
