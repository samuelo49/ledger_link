"""add wallet holds table

Revision ID: 20251107_0003
Revises: 20251102_0002_wallet_tables.py
Create Date: 2025-11-07 00:03:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251107_0003"
down_revision = "20251102_0002_wallet_tables.py"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_holds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_id", sa.Integer(), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("reference", sa.String(length=64), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ledger_entry_id", sa.Integer(), sa.ForeignKey("ledger_entries.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_wallet_holds_wallet_id", "wallet_holds", ["wallet_id"])
    op.create_unique_constraint("uq_wallet_hold_idem", "wallet_holds", ["wallet_id", "idempotency_key"])


def downgrade() -> None:
    op.drop_constraint("uq_wallet_hold_idem", "wallet_holds", type_="unique")
    op.drop_index("ix_wallet_holds_wallet_id", table_name="wallet_holds")
    op.drop_table("wallet_holds")
