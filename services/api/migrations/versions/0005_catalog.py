"""Cria catálogo: serviços, pacotes e planos de assinatura com RLS.

Revision ID: 0005_catalog
Revises: 0004_user_commissions
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0005_catalog"
down_revision: str | None = "0004_user_commissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "buffer_minutes",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "cost",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "requires_deposit",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "deposit_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=True,
        ),
        sa.Column(
            "show_average_price",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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
            "duration_minutes >= 5",
            name="ck_services_duration_minutes",
        ),
        sa.CheckConstraint(
            "buffer_minutes >= 0",
            name="ck_services_buffer_minutes",
        ),
        sa.CheckConstraint("price >= 0", name="ck_services_price"),
        sa.CheckConstraint("cost >= 0", name="ck_services_cost"),
        sa.CheckConstraint(
            "deposit_amount IS NULL OR deposit_amount >= 0",
            name="ck_services_deposit_amount",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_services_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_services"),
    )
    op.create_index("ix_services_tenant_id", "services", ["tenant_id"])

    op.create_table(
        "packages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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
        sa.CheckConstraint("total_price >= 0", name="ck_packages_total_price"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_packages_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_packages"),
    )
    op.create_index("ix_packages_tenant_id", "packages", ["tenant_id"])

    op.create_table(
        "package_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "quantity",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity >= 1", name="ck_package_items_quantity"),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["packages.id"],
            name="fk_package_items_package_id_packages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_package_items_service_id_services",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_package_items_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_package_items"),
        sa.UniqueConstraint(
            "package_id",
            "service_id",
            name="uq_package_items_package_id_service_id",
        ),
    )
    op.create_index("ix_package_items_tenant_id", "package_items", ["tenant_id"])
    op.create_index("ix_package_items_package_id", "package_items", ["package_id"])
    op.create_index("ix_package_items_service_id", "package_items", ["service_id"])

    op.execute("CREATE TYPE billing_cycle AS ENUM ('MONTHLY', 'QUARTERLY')")
    op.create_table(
        "subscription_plans",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "billing_cycle",
            postgresql.ENUM(
                "MONTHLY",
                "QUARTERLY",
                name="billing_cycle",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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
        sa.CheckConstraint("price >= 0", name="ck_subscription_plans_price"),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_subscription_plans_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscription_plans"),
    )
    op.create_index(
        "ix_subscription_plans_tenant_id",
        "subscription_plans",
        ["tenant_id"],
    )

    op.create_table(
        "subscription_plan_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uses_per_cycle", sa.Integer(), nullable=False),
        sa.Column("min_interval_days", sa.Integer(), nullable=True),
        sa.Column(
            "allowed_weekdays",
            postgresql.ARRAY(sa.Integer()),
            nullable=True,
        ),
        sa.CheckConstraint(
            "uses_per_cycle >= 1",
            name="ck_subscription_plan_items_uses_per_cycle",
        ),
        sa.CheckConstraint(
            "min_interval_days IS NULL OR min_interval_days >= 0",
            name="ck_subscription_plan_items_min_interval_days",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
            name="fk_subscription_plan_items_plan_id_subscription_plans",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_subscription_plan_items_service_id_services",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_subscription_plan_items_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscription_plan_items"),
        sa.UniqueConstraint(
            "plan_id",
            "service_id",
            name="uq_subscription_plan_items_plan_id_service_id",
        ),
    )
    op.create_index(
        "ix_subscription_plan_items_tenant_id",
        "subscription_plan_items",
        ["tenant_id"],
    )
    op.create_index(
        "ix_subscription_plan_items_plan_id",
        "subscription_plan_items",
        ["plan_id"],
    )
    op.create_index(
        "ix_subscription_plan_items_service_id",
        "subscription_plan_items",
        ["service_id"],
    )

    # RLS: todas as tabelas do catálogo são isoladas por tenant.
    op.execute("ALTER TABLE services ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE services FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY services_tenant_isolation ON services "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )

    op.execute("ALTER TABLE packages ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE packages FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY packages_tenant_isolation ON packages "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )

    op.execute("ALTER TABLE package_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE package_items FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY package_items_tenant_isolation ON package_items "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )

    op.execute("ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE subscription_plans FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY subscription_plans_tenant_isolation ON subscription_plans "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )

    op.execute("ALTER TABLE subscription_plan_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE subscription_plan_items FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY subscription_plan_items_tenant_isolation ON subscription_plan_items "
        "USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
    )


def downgrade() -> None:
    op.drop_table("subscription_plan_items")
    op.drop_table("subscription_plans")
    op.drop_table("package_items")
    op.drop_table("packages")
    op.drop_table("services")
    op.execute("DROP TYPE IF EXISTS billing_cycle")
