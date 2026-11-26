"""Comanda digital e vínculo de crédito com a venda.

Revision ID: 0021_sales
Revises: 0020_business_profile
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_sales"
down_revision: str | None = "0020_business_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE sale_status AS ENUM ('OPEN', 'PAID', 'CANCELLED')"
    )
    op.execute(
        "CREATE TYPE sale_item_category AS ENUM "
        "('SERVICE', 'PACKAGE', 'PRODUCT', 'OTHER')"
    )
    op.execute(
        "CREATE TYPE sale_payment_method AS ENUM "
        "('PIX', 'CASH', 'CARD', 'BOLETO', 'TRANSFER', 'OTHER')"
    )

    op.create_table(
        "sales",
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
            "collaborator_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "financial_entry_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "OPEN",
                "PAID",
                "CANCELLED",
                name="sale_status",
                create_type=False,
            ),
            server_default=sa.text("'OPEN'"),
            nullable=False,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "discount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "credit_amount",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "payment_method",
            postgresql.ENUM(
                "PIX",
                "CASH",
                "CARD",
                "BOLETO",
                "TRANSFER",
                "OTHER",
                name="sale_payment_method",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint("subtotal >= 0", name="ck_sales_subtotal"),
        sa.CheckConstraint("discount >= 0", name="ck_sales_discount"),
        sa.CheckConstraint(
            "credit_amount >= 0",
            name="ck_sales_credit_amount",
        ),
        sa.CheckConstraint("total >= 0", name="ck_sales_total"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["financial_accounts.id"],
            name="fk_sales_account_id_financial_accounts",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_sales_appointment_id_appointments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
            name="fk_sales_client_id_clients",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["collaborator_id"],
            ["users.id"],
            name="fk_sales_collaborator_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_sales_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["financial_entry_id"],
            ["financial_entries.id"],
            name="fk_sales_financial_entry_id_financial_entries",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_sales_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
    )
    for column in (
        "tenant_id",
        "client_id",
        "appointment_id",
        "collaborator_id",
        "status",
    ):
        op.create_index(f"ix_sales_{column}", "sales", [column])

    op.create_table(
        "sale_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "service_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "inventory_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "category",
            postgresql.ENUM(
                "SERVICE",
                "PACKAGE",
                "PRODUCT",
                "OTHER",
                name="sale_item_category",
                create_type=False,
            ),
            server_default=sa.text("'SERVICE'"),
            nullable=False,
        ),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column(
            "unit_price",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "cost",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="ck_sale_items_quantity"),
        sa.CheckConstraint(
            "unit_price >= 0",
            name="ck_sale_items_unit_price",
        ),
        sa.CheckConstraint("cost >= 0", name="ck_sale_items_cost"),
        sa.CheckConstraint("total >= 0", name="ck_sale_items_total"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_sale_items_inventory_item_id_inventory_items",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sale_id"],
            ["sales.id"],
            name="fk_sale_items_sale_id_sales",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_sale_items_service_id_services",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_sale_items_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sale_items"),
    )
    for column in ("tenant_id", "sale_id"):
        op.create_index(f"ix_sale_items_{column}", "sale_items", [column])

    op.add_column(
        "client_credit_usages",
        sa.Column(
            "sale_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_client_credit_usages_sale_id_sales",
        "client_credit_usages",
        "sales",
        ["sale_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_client_credit_usages_sale_id",
        "client_credit_usages",
        ["sale_id"],
    )

    for table in ("sales", "sale_items"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            "USING (tenant_id = "
            "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = "
            "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    op.drop_index(
        "ix_client_credit_usages_sale_id",
        table_name="client_credit_usages",
    )
    op.drop_constraint(
        "fk_client_credit_usages_sale_id_sales",
        "client_credit_usages",
        type_="foreignkey",
    )
    op.drop_column("client_credit_usages", "sale_id")
    op.drop_table("sale_items")
    op.drop_table("sales")
    op.execute("DROP TYPE sale_payment_method")
    op.execute("DROP TYPE sale_item_category")
    op.execute("DROP TYPE sale_status")
