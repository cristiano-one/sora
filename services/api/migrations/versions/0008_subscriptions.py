"""Cria assinaturas de clientes e consumo de cotas com RLS.

Revision ID: 0008_subscriptions
Revises: 0007_appointments
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0008_subscriptions"
down_revision: str | None = "0007_appointments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE client_subscription_status AS ENUM ("
        "'PENDING_PAYMENT', 'ACTIVE', 'CANCELLED', 'EXPIRED')"
    )

    op.create_table(
        "client_subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING_PAYMENT",
                "ACTIVE",
                "CANCELLED",
                "EXPIRED",
                name="client_subscription_status",
                create_type=False,
            ),
            server_default=sa.text("'ACTIVE'"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "current_period_start",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "current_period_end",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
            "current_period_end > current_period_start",
            name="ck_client_subscriptions_period",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_client_subscriptions_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
            name="fk_client_subscriptions_plan_id_subscription_plans",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_client_subscriptions_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_client_subscriptions"),
    )
    op.create_index(
        "ix_client_subscriptions_tenant_id",
        "client_subscriptions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_client_subscriptions_client_id",
        "client_subscriptions",
        ["client_id"],
    )
    op.create_index(
        "ix_client_subscriptions_plan_id",
        "client_subscriptions",
        ["plan_id"],
    )
    op.create_index(
        "ix_client_subscriptions_status",
        "client_subscriptions",
        ["status"],
    )

    op.create_table(
        "subscription_usages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "appointment_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "period_end > period_start",
            name="ck_subscription_usages_period",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_subscription_usages_appointment_id_appointments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_subscription_usages_client_id_clients",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_subscription_usages_service_id_services",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["client_subscriptions.id"],
            name="fk_subscription_usages_subscription_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_subscription_usages_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscription_usages"),
        sa.UniqueConstraint(
            "appointment_id",
            name="uq_subscription_usages_appointment_id",
        ),
    )
    op.create_index(
        "ix_subscription_usages_tenant_id",
        "subscription_usages",
        ["tenant_id"],
    )
    op.create_index(
        "ix_subscription_usages_subscription_id",
        "subscription_usages",
        ["subscription_id"],
    )
    op.create_index(
        "ix_subscription_usages_client_id",
        "subscription_usages",
        ["client_id"],
    )
    op.create_index(
        "ix_subscription_usages_service_id",
        "subscription_usages",
        ["service_id"],
    )
    op.create_index(
        "ix_subscription_usages_appointment_id",
        "subscription_usages",
        ["appointment_id"],
    )

    for table in ("client_subscriptions", "subscription_usages"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = "
            "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    op.drop_table("subscription_usages")
    op.drop_table("client_subscriptions")
    op.execute("DROP TYPE IF EXISTS client_subscription_status")
