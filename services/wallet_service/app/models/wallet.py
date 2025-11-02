from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.wallet_service.app.db.base import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    # Stored, authoritative balance (use DECIMAL for money)
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # relationships
    entries = relationship(
        "LedgerEntry",
        back_populates="wallet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
