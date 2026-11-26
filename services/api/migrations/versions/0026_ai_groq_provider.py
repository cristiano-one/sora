"""Provedor de IA por tenant (Groq) e chave cifrada.

Revision ID: 0026_ai_groq_provider
Revises: 0025_whatsapp_tech_provider
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_ai_groq_provider"
down_revision: str | None = "0025_whatsapp_tech_provider"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_settings",
        sa.Column(
            "ai_provider",
            sa.String(length=20),
            server_default=sa.text("'mock'"),
            nullable=False,
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column(
            "ai_model",
            sa.String(length=100),
            server_default=sa.text("'llama-3.3-70b-versatile'"),
            nullable=False,
        ),
    )
    op.add_column(
        "tenant_settings",
        sa.Column("ai_api_key_encrypted", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_tenant_settings_ai_provider",
        "tenant_settings",
        "ai_provider IN ('mock', 'groq')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_tenant_settings_ai_provider",
        "tenant_settings",
        type_="check",
    )
    op.drop_column("tenant_settings", "ai_api_key_encrypted")
    op.drop_column("tenant_settings", "ai_model")
    op.drop_column("tenant_settings", "ai_provider")
