"""Cria intents de pagamento Pix com RLS.

Revision ID: 0011_payment_intents
Revises: 0010_tenant_settings_deposit
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0011_payment_intents"
down_revision: str | None = "0010_tenant_settings_deposit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE payment_status AS ENUM "
        "('PENDING', 'PAID', 'EXPIRED', 'CANCELLED')"
    )

    op.create_table(
        "payment_intents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "PAID",
                "EXPIRED",
                "CANCELLED",
                name="payment_status",
                create_type=False,
            ),
            server_default=sa.text("'PENDING'"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            server_default=sa.text("'mock'"),
            nullable=False,
        ),
        sa.Column("pix_payload", sa.Text(), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("amount > 0", name="ck_payment_intents_amount"),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_payment_intents_appointment_id_appointments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_payment_intents_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["client_subscriptions.id"],
            name="fk_payment_intents_subscription_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_payment_intents_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_payment_intents"),
    )
    op.create_index(
        "ix_payment_intents_tenant_id",
        "payment_intents",
        ["tenant_id"],
    )
    op.create_index(
        "ix_payment_intents_client_id",
        "payment_intents",
        ["client_id"],
    )
    op.create_index(
        "ix_payment_intents_appointment_id",
        "payment_intents",
        ["appointment_id"],
    )
    op.create_index(
        "ix_payment_intents_subscription_id",
        "payment_intents",
        ["subscription_id"],
    )
    op.create_index(
        "ix_payment_intents_status",
        "payment_intents",
        ["status"],
    )

    op.execute("ALTER TABLE payment_intents ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE payment_intents FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY payment_intents_tenant_isolation ON payment_intents "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = "
        "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("payment_intents")
    op.execute("DROP TYPE IF EXISTS payment_status")
