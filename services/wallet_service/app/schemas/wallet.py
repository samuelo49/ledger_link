from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field


class WalletCreate(BaseModel):
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code, e.g. USD")


class WalletResponse(BaseModel):
    id: int
    owner_user_id: int
    currency: str
    status: str
    balance: Decimal


class MoneyChangeRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    idempotency_key: str | None = Field(None, max_length=64)
    details: dict | None = Field(None, description="Optional metadata payload persisted with the ledger entry")


class BalanceResponse(BaseModel):
    id: int
    currency: str
    balance: Decimal
