"""Add wallet transfers and outbox tables

Revision ID: wallet_20251107_0004
Revises: 20251107_0003_wallet_holds
Create Date: 2025-11-07 00:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "wallet_20251107_0004"
down_revision = "20251107_0003_wallet_holds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wallet_transfers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_wallet_id", sa.Integer(), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_wallet_id", sa.Integer(), sa.ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("failure_reason", sa.String(length=128), nullable=True),
        sa.Column("external_reference", sa.String(length=64), nullable=True),
        sa.Column("ledger_debit_entry_id", sa.Integer(), sa.ForeignKey("ledger_entries.id"), nullable=True),
        sa.Column("ledger_credit_entry_id", sa.Integer(), sa.ForeignKey("ledger_entries.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_wallet_transfer_idem"),
    )
    op.create_index("ix_wallet_transfer_source_created", "wallet_transfers", ["source_wallet_id", "created_at"])
    op.create_index("ix_wallet_transfer_user", "wallet_transfers", ["user_id"])

    op.create_table(
        "wallet_outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_wallet_outbox_processed", "wallet_outbox_events", ["processed_at"])


def downgrade() -> None:
    op.drop_index("ix_wallet_outbox_processed", table_name="wallet_outbox_events")
    op.drop_table("wallet_outbox_events")
    op.drop_index("ix_wallet_transfer_source_created", table_name="wallet_transfers")
    op.drop_index("ix_wallet_transfer_user", table_name="wallet_transfers")
    op.drop_table("wallet_transfers")
