"""Campos de perfil e endereço do cliente.

Revision ID: 0028_client_profile
Revises: 0027_ai_inbox_permission
Create Date: 2026-11-26

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_client_profile"
down_revision: str | None = "0027_ai_inbox_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column, kind in (
        ("address_zip", sa.String(length=9)),
        ("address_street", sa.String(length=255)),
        ("address_number", sa.String(length=20)),
        ("address_complement", sa.String(length=120)),
        ("address_neighborhood", sa.String(length=120)),
        ("address_city", sa.String(length=120)),
        ("address_state", sa.String(length=2)),
        ("notes_encrypted", sa.Text()),
    ):
        op.add_column("clients", sa.Column(column, kind, nullable=True))


def downgrade() -> None:
    for column in (
        "notes_encrypted",
        "address_state",
        "address_city",
        "address_neighborhood",
        "address_complement",
        "address_number",
        "address_street",
        "address_zip",
    ):
        op.drop_column("clients", column)
