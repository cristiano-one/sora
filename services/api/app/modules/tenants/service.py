"""Cadastro de empresa (tenant) + OWNER inicial sob RLS."""

from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.security import hash_password
from app.db.rls import set_tenant_context
from app.models import TaxRegime, Tenant, User, UserRole


class SlugAlreadyExistsError(Exception):
    """Slug de tenant já utilizado."""


def _is_slug_conflict(error: IntegrityError) -> bool:
    """Identifica a violação da unique constraint de slug do tenant."""
    candidates = (error.orig, getattr(error.orig, "__cause__", None))
    for candidate in candidates:
        if getattr(candidate, "constraint_name", None) == "uq_tenants_slug":
            return True
    return "uq_tenants_slug" in str(error.orig)


async def create_tenant_with_owner(
    session: AsyncSession,
    *,
    name: str,
    slug: str,
    tax_regime: TaxRegime,
    owner_full_name: str,
    owner_email: str,
    owner_password: str,
) -> tuple[Tenant, User]:
    """Cria o tenant e seu OWNER na mesma transação, com contexto RLS."""
    tenant_id = uuid4()

    # A RLS exige app.current_tenant_id já definido para o INSERT do próprio
    # tenant (WITH CHECK id = current_setting) e do usuário (tenant_id = ...).
    await set_tenant_context(session, tenant_id)

    tenant = Tenant(
        id=tenant_id,
        name=name.strip(),
        slug=slug.strip().lower(),
        tax_regime=tax_regime,
    )
    owner = User(
        tenant_id=tenant_id,
        email=owner_email.strip().lower(),
        hashed_password=hash_password(owner_password),
        full_name=owner_full_name.strip(),
        role=UserRole.OWNER,
        is_active=True,
    )
    session.add_all([tenant, owner])

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        if _is_slug_conflict(exc):
            raise SlugAlreadyExistsError from exc
        raise

    return tenant, owner
