"""Registro de auditoria imutável de ações sensíveis."""

from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import Principal
from app.db.rls import set_tenant_context
from app.models import AuditLog


def client_ip(request: Request) -> str | None:
    """Extrai o IP do cliente (respeitando X-Forwarded-For do proxy)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def record_audit(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    actor: Principal | None,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None,
    ip_address: str | None,
    details: dict[str, object] | None = None,
) -> None:
    """Grava o AuditLog (append-only) no tenant atual.

    Reaplica o contexto RLS porque a operação principal normalmente já
    encerrou a transação anterior com commit.
    """
    await set_tenant_context(session, tenant_id)
    session.add(
        AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor.user_id if actor is not None else None,
            actor_role=actor.role.value if actor is not None else "SYSTEM",
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            ip_address=ip_address,
            details=details,
        )
    )
    await session.commit()
