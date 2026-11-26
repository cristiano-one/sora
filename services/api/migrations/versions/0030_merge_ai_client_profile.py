"""Mescla as migrations de IA e de perfil do cliente.

As duas linhas nasceram de 0027/0028 e precisam convergir para um único head.

Revision ID: 0030_merge_ai_client_profile
Revises: 0028_client_profile, 0029_ai_default_model
Create Date: 2026-11-26

"""

from collections.abc import Sequence

revision: str = "0030_merge_ai_client_profile"
down_revision: tuple[str, str] | None = (
    "0028_client_profile",
    "0029_ai_default_model",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Nada a alterar: apenas une os dois heads do grafo."""


def downgrade() -> None:
    """Nada a desfazer: as migrations originais cuidam dos próprios dados."""
