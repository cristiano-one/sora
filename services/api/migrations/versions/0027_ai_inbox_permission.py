"""Permissão de acesso ao inbox da SORA IA por usuário.

Revision ID: 0027_ai_inbox_permission
Revises: 0026_ai_groq_provider
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027_ai_inbox_permission"
down_revision: str | None = "0026_ai_groq_provider"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "can_manage_ai_inbox",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "can_manage_ai_inbox")
