"""Contratos de resposta do módulo de tenants."""

from uuid import UUID

from pydantic import BaseModel


class CurrentTenantResponse(BaseModel):
    """Dados públicos do tenant atual."""

    id: UUID
    name: str
    slug: str
