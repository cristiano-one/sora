"""Troca o modelo padrão de chat para um disponível fora do plano Enterprise.

`llama-3.3-70b-versatile` e `llama-3.1-8b-instant` são modelos Enterprise na
Groq; `openai/gpt-oss-120b` é o modelo de produção disponível no plano
Developer/Free.

Revision ID: 0029_ai_default_model
Revises: 0028_ai_transcription_model
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_ai_default_model"
down_revision: str | None = "0028_ai_transcription_model"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_MODEL = "llama-3.3-70b-versatile"
NEW_MODEL = "openai/gpt-oss-120b"


def upgrade() -> None:
    op.alter_column(
        "tenant_settings",
        "ai_model",
        server_default=sa.text(f"'{NEW_MODEL}'"),
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )
    op.execute(
        sa.text(
            "UPDATE tenant_settings SET ai_model = :new_model WHERE ai_model = :old_model"
        ).bindparams(new_model=NEW_MODEL, old_model=OLD_MODEL)
    )


def downgrade() -> None:
    op.alter_column(
        "tenant_settings",
        "ai_model",
        server_default=sa.text(f"'{OLD_MODEL}'"),
        existing_type=sa.String(length=100),
        existing_nullable=False,
    )
