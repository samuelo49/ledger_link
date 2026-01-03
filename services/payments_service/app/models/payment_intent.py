from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import String, Numeric, text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import BaseModel


class PaymentIntentStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    declined = "declined"
    review = "review"
    canceled = "canceled"


class PaymentIntent(BaseModel):
    __tablename__ = "payment_intents"

    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    wallet_id: Mapped[int] = mapped_column(index=True, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    status: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        server_default=text("'pending'"),
    )

    hold_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
