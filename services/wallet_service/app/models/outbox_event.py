from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, JSON, DateTime, text, Index
from sqlalchemy.orm import Mapped, mapped_column

from services.wallet_service.app.db.base import Base


class OutboxEvent(Base):
    __tablename__ = "wallet_outbox_events"
    __table_args__ = (
        Index("ix_wallet_outbox_processed", "processed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
