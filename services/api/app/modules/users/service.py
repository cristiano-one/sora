"""Regras de cadastro e comissão de colaboradores."""

from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependencies import Principal
from app.core.auth.security import hash_password
from app.models import CommissionBase, User, UserRole

_ALLOWED_UPDATE_FIELDS = frozenset(
    {
        "full_name",
        "is_active",
        "role",
        "commission_percentage",
        "commission_fixed",
        "commission_base",
    }
)


class InvalidRoleChangeError(Exception):
    """Papel/alteração não permitida para o ator autenticado."""


class EmailAlreadyExistsError(Exception):
    """E-mail já cadastrado no tenant."""


class CannotDeleteUserError(Exception):
    """Usuário protegido (owner/próprio/escopo) não pode ser excluído."""


class UserInUseError(Exception):
    """Usuário possui vínculos e não pode ser excluído."""


def _validate_create_role(actor: Principal, role: UserRole) -> None:
    if role == UserRole.OWNER:
        raise InvalidRoleChangeError
    if actor.role == UserRole.ADMIN and role != UserRole.COLLABORATOR:
        raise InvalidRoleChangeError


def _validate_update(
    actor: Principal,
    target: User,
    changes: dict[str, object],
) -> None:
    if target.role == UserRole.OWNER and actor.role != UserRole.OWNER:
        raise InvalidRoleChangeError

    new_role = changes.get("role")
    if new_role is not None:
        if new_role == UserRole.OWNER:
            raise InvalidRoleChangeError
        if actor.role == UserRole.ADMIN and new_role != UserRole.COLLABORATOR:
            raise InvalidRoleChangeError

    if target.id == actor.user_id and ("role" in changes or "is_active" in changes):
        raise InvalidRoleChangeError


async def create_user(
    session: AsyncSession,
    *,
    actor: Principal,
    full_name: str,
    email: str,
    password: str,
    role: UserRole,
    commission_percentage: Decimal | None,
    commission_fixed: Decimal | None,
    commission_base: CommissionBase,
) -> User:
    """Cria um colaborador/admin no tenant do ator (RLS já aplicada)."""
    _validate_create_role(actor, role)

    user = User(
        tenant_id=actor.tenant_id,
        email=email.strip().lower(),
        hashed_password=hash_password(password),
        full_name=full_name.strip(),
        role=role,
        is_active=True,
        commission_percentage=commission_percentage,
        commission_fixed=commission_fixed,
        commission_base=commission_base,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise EmailAlreadyExistsError from exc
    return user


async def update_user(
    session: AsyncSession,
    *,
    actor: Principal,
    target: User,
    changes: dict[str, object],
) -> User:
    """Aplica alterações parciais validadas por papel."""
    _validate_update(actor, target, changes)
    for field in _ALLOWED_UPDATE_FIELDS:
        if field in changes:
            setattr(target, field, changes[field])
    await session.commit()
    return target


async def delete_user(
    session: AsyncSession,
    *,
    actor: Principal,
    target: User,
) -> None:
    """Exclui usuário sem vínculos, preservando OWNER e o próprio ator."""
    if target.id == actor.user_id or target.role == UserRole.OWNER:
        raise CannotDeleteUserError
    if actor.role == UserRole.ADMIN and target.role != UserRole.COLLABORATOR:
        raise CannotDeleteUserError
    await session.delete(target)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise UserInUseError from exc
