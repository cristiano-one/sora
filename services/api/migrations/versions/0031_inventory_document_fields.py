"""Dados de nota fiscal/recibo nas entradas de estoque.

Revision ID: 0031_inventory_document_fields
Revises: 0030_merge_ai_client_profile
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_inventory_document_fields"
down_revision: str | None = "0030_merge_ai_client_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    ("document_type", sa.String(length=20)),
    ("document_number", sa.String(length=60)),
    ("document_series", sa.String(length=20)),
    ("supplier_name", sa.String(length=255)),
    ("supplier_tax_id", sa.String(length=20)),
    ("issue_date", sa.Date()),
    ("total_amount", sa.Numeric(12, 2)),
    ("payment_method", sa.String(length=30)),
    ("access_key", sa.String(length=44)),
)


def upgrade() -> None:
    for name, kind in _COLUMNS:
        op.add_column(
            "stock_movements",
            sa.Column(name, kind, nullable=True),
        )
    op.create_check_constraint(
        "ck_stock_movements_total_amount",
        "stock_movements",
        "total_amount IS NULL OR total_amount >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_stock_movements_total_amount",
        "stock_movements",
        type_="check",
    )
    for name, _ in reversed(_COLUMNS):
        op.drop_column("stock_movements", name)
