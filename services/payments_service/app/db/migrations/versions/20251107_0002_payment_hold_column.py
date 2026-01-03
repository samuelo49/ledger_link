"""Add hold_id column to payment intents

Revision ID: payments_20251107_0002
Revises: payments_20251030_0001
Create Date: 2025-11-07 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "payments_20251107_0002"
down_revision = "payments_20251030_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("payment_intents", sa.Column("hold_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("payment_intents", "hold_id")
