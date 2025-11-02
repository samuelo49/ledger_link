"""wallet tables

Revision ID: wallet_20251102_0002
Revises: wallet_20251030_0001
Create Date: 2025-11-02 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "wallet_20251102_0002"
down_revision = "wallet_20251030_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("owner_user_id", "currency", name="uq_wallet_owner_currency"),
    )
    op.create_index("ix_wallet_owner", "wallets", ["owner_user_id"])  # explicit for some backends

    op.create_table(
        "ledger_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("wallet_id", sa.Integer(), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Index("ix_ledger_wallet_created", "wallet_id", "created_at"),
        sa.UniqueConstraint("wallet_id", "idempotency_key", name="uq_ledger_wallet_idem"),
    )
    op.create_index("ix_ledger_wallet", "ledger_entries", ["wallet_id"])  # explicit


def downgrade() -> None:
    op.drop_index("ix_ledger_wallet", table_name="ledger_entries")
    op.drop_table("ledger_entries")
    op.drop_index("ix_wallet_owner", table_name="wallets")
    op.drop_table("wallets")
