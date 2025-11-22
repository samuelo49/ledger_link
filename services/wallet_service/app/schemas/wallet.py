from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field
from pydantic import ConfigDict


class WalletCreate(BaseModel):
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code, e.g. USD")


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
