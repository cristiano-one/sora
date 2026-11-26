"""Créditos de aniversário e valor configurável por crédito.

Revision ID: 0014_birthday_credits
Revises: 0013_ai_conversations
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0014_birthday_credits"
down_revision: str | None = "0013_ai_conversations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_credits",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "used_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "reason",
            sa.String(length=50),
            server_default=sa.text("'BIRTHDAY'"),
            nullable=False,
        ),
        sa.Column("reference", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_client_credits_amount"),
        sa.CheckConstraint(
            "used_amount >= 0 AND used_amount <= amount",
            name="ck_client_credits_used_amount",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_client_credits_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_client_credits_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_client_credits"),
        sa.UniqueConstraint(
            "tenant_id",
            "client_id",
            "reason",
            "reference",
            name="uq_client_credits_tenant_client_reason_reference",
        ),
    )
    op.create_index(
        "ix_client_credits_tenant_id",
        "client_credits",
        ["tenant_id"],
    )
    op.create_index(
        "ix_client_credits_client_id",
        "client_credits",
        ["client_id"],
    )

    op.add_column(
        "tenant_settings",
        sa.Column(
            "birthday_credit_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_tenant_settings_birthday_credit_amount",
        "tenant_settings",
        "birthday_credit_amount >= 0",
    )

    op.execute("ALTER TABLE client_credits ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE client_credits FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY client_credits_tenant_isolation ON client_credits "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("client_credits")
    op.drop_constraint(
        "ck_tenant_settings_birthday_credit_amount",
        "tenant_settings",
        type_="check",
    )
    op.drop_column("tenant_settings", "birthday_credit_amount")
