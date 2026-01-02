from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_verified: Mapped[bool] = mapped_column(default=False)
    is_superuser: Mapped[bool] = mapped_column(default=False)
    roles: Mapped[str] = mapped_column(String(255), default="customer")
    # Security and audit fields
    last_login_at: Mapped[Optional[datetime]] = mapped_column(default=None, nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_at: Mapped[Optional[datetime]] = mapped_column(default=None, nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    # Email verification and password reset flows
    verification_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, default=None)
    verified_at: Mapped[Optional[datetime]] = mapped_column(default=None, nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, default=None)
    password_reset_sent_at: Mapped[Optional[datetime]] = mapped_column(default=None, nullable=True)
    # Soft delete and extensible profile metadata
    deleted_at: Mapped[Optional[datetime]] = mapped_column(default=None, nullable=True)
    profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
