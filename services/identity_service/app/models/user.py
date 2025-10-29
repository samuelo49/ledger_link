from __future__ import annotations

from datetime import datetime
from typing import Annotated

from sqlalchemy import String, text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class User(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    roles: Mapped[str] = mapped_column(String(255), default="customer")
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=datetime.utcnow,
        nullable=False,
    )
