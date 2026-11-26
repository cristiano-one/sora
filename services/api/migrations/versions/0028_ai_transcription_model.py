"""Modelo de transcrição de voz por clínica.

Revision ID: 0028_ai_transcription_model
Revises: 0027_ai_inbox_permission
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_ai_transcription_model"
down_revision: str | None = "0027_ai_inbox_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_settings",
        sa.Column(
            "ai_transcription_model",
            sa.String(length=100),
            server_default=sa.text("'whisper-large-v3-turbo'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_settings", "ai_transcription_model")
