"""extend user model with audit, security, metadata

Revision ID: 20251030_0002
Revises: 20251030_0001
Create Date: 2025-10-30 21:59:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251030_0002"
down_revision = "20251030_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("users", sa.Column("locked_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("users", sa.Column("mfa_secret", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("verification_token", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("verified_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("users", sa.Column("password_reset_token", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("password_reset_sent_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=False), nullable=True))
    op.add_column("users", sa.Column("profile", sa.JSON(), nullable=True))

    # Indexes for querying and constraints
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"], unique=False)

    # Case-insensitive unique index on email using functional index lower(email)
    # Note: Keep the existing case-sensitive unique constraint for now; this enforces CI uniqueness additionally.
    op.create_index("uq_users_email_ci", "users", [sa.text("lower(email)")], unique=True)


def downgrade() -> None:
    # Drop the functional unique index and other indexes
    op.drop_index("uq_users_email_ci", table_name="users")
    op.drop_index("ix_users_deleted_at", table_name="users")
    op.drop_index("ix_users_created_at", table_name="users")

    # Drop the added columns
    op.drop_column("users", "profile")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "password_reset_sent_at")
    op.drop_column("users", "password_reset_token")
    op.drop_column("users", "verified_at")
    op.drop_column("users", "verification_token")
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "locked_at")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "last_login_at")
