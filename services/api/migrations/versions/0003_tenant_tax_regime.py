"""Adiciona o regime tributário (MEI/COMPLETE) ao tenant.

Revision ID: 0003_tenant_tax_regime
Revises: 0002_auth_tenant_lookup
Create Date: 2026-11-25

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Identificadores da revisão, usados pelo Alembic.
revision: str = "0003_tenant_tax_regime"
down_revision: str | None = "0002_auth_tenant_lookup"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE tax_regime AS ENUM ('MEI', 'COMPLETE')")
    op.add_column(
        "tenants",
        sa.Column(
            "tax_regime",
            postgresql.ENUM(
                "MEI",
                "COMPLETE",
                name="tax_regime",
                create_type=False,
            ),
            server_default=sa.text("'COMPLETE'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "tax_regime")
    op.execute("DROP TYPE IF EXISTS tax_regime")
