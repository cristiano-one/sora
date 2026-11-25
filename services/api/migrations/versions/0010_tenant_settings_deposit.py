"""Configurações do tenant e expiração de reserva com sinal.

Revision ID: 0010_tenant_settings_deposit
Revises: 0009_appointment_subscription
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0010_tenant_settings_deposit"
down_revision: str | None = "0009_appointment_subscription"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenant_settings",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deposit_score_threshold", sa.Integer(), nullable=True),
        sa.Column(
            "deposit_amount_low_score",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "theme_primary_color",
            sa.String(length=7),
            server_default=sa.text("'#4f46e5'"),
            nullable=False,
        ),
        sa.Column(
            "agent_name",
            sa.String(length=100),
            server_default=sa.text("'Sora'"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "deposit_score_threshold IS NULL OR "
            "(deposit_score_threshold >= 0 AND deposit_score_threshold <= 100)",
            name="ck_tenant_settings_deposit_score_threshold",
        ),
        sa.CheckConstraint(
            "deposit_amount_low_score IS NULL OR deposit_amount_low_score >= 0",
            name="ck_tenant_settings_deposit_amount_low_score",
        ),
        sa.CheckConstraint(
            "theme_primary_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_tenant_settings_theme_color",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_tenant_settings_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("tenant_id", name="pk_tenant_settings"),
    )

    op.add_column(
        "appointments",
        sa.Column(
            "deposit_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.execute("ALTER TABLE tenant_settings ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_settings FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY tenant_settings_tenant_isolation ON tenant_settings "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("tenant_settings")
    op.drop_column("appointments", "deposit_expires_at")
