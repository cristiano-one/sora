"""Estoque de insumos e movimentações.

Revision ID: 0015_inventory
Revises: 0014_birthday_credits
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_inventory"
down_revision: str | None = "0014_birthday_credits"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TENANT_POLICY = (
    "USING (tenant_id = "
    "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid) "
    "WITH CHECK (tenant_id = "
    "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)"
)


def upgrade() -> None:
    op.create_table(
        "inventory_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "unit",
            sa.String(length=20),
            server_default=sa.text("'un'"),
            nullable=False,
        ),
        sa.Column(
            "quantity",
            sa.Numeric(precision=12, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "min_quantity",
            sa.Numeric(precision=12, scale=3),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "unit_cost",
            sa.Numeric(precision=12, scale=2),
            server_default=sa.text("0"),
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
            "quantity >= 0 AND min_quantity >= 0 AND unit_cost >= 0",
            name="ck_inventory_items_values",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_inventory_items_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_inventory_items"),
        sa.UniqueConstraint(
            "tenant_id",
            "name",
            name="uq_inventory_items_tenant_id_name",
        ),
    )
    op.create_index(
        "ix_inventory_items_tenant_id",
        "inventory_items",
        ["tenant_id"],
    )

    op.create_table(
        "stock_movements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=12, scale=3),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
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
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_stock_movements_quantity",
        ),
        sa.CheckConstraint(
            "kind IN ('IN', 'OUT', 'ADJUSTMENT')",
            name="ck_stock_movements_kind",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_stock_movements_created_by_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["inventory_items.id"],
            name="fk_stock_movements_item_id_inventory_items",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_stock_movements_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_stock_movements"),
    )
    op.create_index(
        "ix_stock_movements_tenant_id",
        "stock_movements",
        ["tenant_id"],
    )
    op.create_index(
        "ix_stock_movements_item_id",
        "stock_movements",
        ["item_id"],
    )

    for table in ("inventory_items", "stock_movements"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_isolation ON {table} "
            + _TENANT_POLICY
        )


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_table("inventory_items")
