from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class PaymentIntentCreate(BaseModel):
    wallet_id: int
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)


class PaymentIntentResponse(BaseModel):
    id: int
    user_id: int
    wallet_id: int
    amount: Decimal
    currency: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class PaymentIntentConfirmRequest(BaseModel):
    # Optionally future fields (e.g., payment method id). Placeholder for now.
    pass
