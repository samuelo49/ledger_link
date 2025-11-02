from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field


class WalletCreate(BaseModel):
    owner_user_id: int = Field(..., ge=1)
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
    metadata: dict | None = None


class BalanceResponse(BaseModel):
    id: int
    currency: str
    balance: Decimal
