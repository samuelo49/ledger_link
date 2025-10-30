"""initial empty revision

Revision ID: wallet_20251030_0001
Revises: 
Create Date: 2025-10-30 00:00:00

"""
from __future__ import annotations

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401

revision = "wallet_20251030_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op initial migration to initialize the migration history
    pass


def downgrade() -> None:
    pass
