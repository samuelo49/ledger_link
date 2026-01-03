from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import ForeignKey, JSON, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.wallet_service.app.db.base import Base


class HoldStatus(str, Enum):
    active = "active"
    captured = "captured"
    released = "released"


class Hold(Base):
    __tablename__ = "wallet_holds"
    __table_args__ = (
        UniqueConstraint("wallet_id", "idempotency_key", name="uq_wallet_hold_idem"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=HoldStatus.active.value)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    ledger_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    wallet = relationship("Wallet", back_populates="holds")
