from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import String, Numeric, UniqueConstraint, Index, ForeignKey, text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from services.wallet_service.app.db.base import Base


class TransferStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    reversed = "reversed"


class Transfer(Base):
    __tablename__ = "wallet_transfers"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_wallet_transfer_idem"),
        Index("ix_wallet_transfer_source_created", "source_wallet_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True, nullable=False)
    source_wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    target_wallet_id: Mapped[int] = mapped_column(ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default=TransferStatus.pending.value, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ledger_debit_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)
    ledger_credit_entry_id: Mapped[int | None] = mapped_column(ForeignKey("ledger_entries.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"), nullable=False
    )
