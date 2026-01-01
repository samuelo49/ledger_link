"""Initial risk service schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "risk_20251030_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    riskdecision = sa.Enum("approve", "review", "decline", name="riskdecision")
    riskdecision.create(op.get_bind(), checkfirst=True)
    riskruletype = sa.Enum(
        "amount_threshold",
        "country_mismatch",
        "blocklist_country",
        "email_domain_block",
        name="riskruletype",
    )
    riskruletype.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "risk_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "event_types",
            postgresql.ARRAY(sa.String(length=64)),
            nullable=False,
        ),
        sa.Column("rule_type", riskruletype, nullable=False),
        sa.Column("action", riskdecision, nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.sql.expression.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "risk_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("decision", riskdecision, nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("triggered_rules", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_risk_evaluations_event_type", "risk_evaluations", ["event_type"])
    op.create_index("ix_risk_evaluations_subject_id", "risk_evaluations", ["subject_id"])
    op.create_index("ix_risk_evaluations_user_id", "risk_evaluations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_risk_evaluations_user_id", table_name="risk_evaluations")
    op.drop_index("ix_risk_evaluations_subject_id", table_name="risk_evaluations")
    op.drop_index("ix_risk_evaluations_event_type", table_name="risk_evaluations")
    op.drop_table("risk_evaluations")
    op.drop_table("risk_rules")
    riskruletype = sa.Enum(
        "amount_threshold",
        "country_mismatch",
        "blocklist_country",
        "email_domain_block",
        name="riskruletype",
    )
    riskdecision = sa.Enum("approve", "review", "decline", name="riskdecision")
    riskruletype.drop(op.get_bind(), checkfirst=True)
    riskdecision.drop(op.get_bind(), checkfirst=True)
