"""Endpoints de colaboradores/usuários e comissões."""

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.users import (
    CommissionResponse,
    UserCreateRequest,
    UserInviteRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.core.auth.dependencies import (
    Principal,
    get_current_principal,
    get_tenant_session,
    require_roles,
)
from app.core.auth.security import invite_key
from app.core.auth.service import revoke_all_sessions
from app.core.config import settings
from app.core.email import send_email
from app.core.redis import get_redis
from app.models import Tenant, User, UserRole
from app.modules.users.service import (
    CannotDeleteUserError,
    EmailAlreadyExistsError,
    InvalidRoleChangeError,
    UserInUseError,
    create_user,
    delete_user,
    update_user,
)

router = APIRouter(prefix="/users", tags=["users"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


@router.get(
    "",
    response_model=list[UserResponse],
    summary="Lista usuários do tenant",
)
async def list_users(
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[User]:
    result = await session.scalars(
        select(User)
        .where(User.tenant_id == principal.tenant_id)
        .order_by(User.full_name)
    )
    return list(result.all())


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra colaborador/admin",
)
async def create_user_endpoint(
    body: UserCreateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> User:
    try:
        return await create_user(
            session,
            actor=principal,
            full_name=body.full_name,
            email=str(body.email),
            password=body.password,
            role=body.role,
            commission_percentage=body.commission_percentage,
            commission_fixed=body.commission_fixed,
            commission_base=body.commission_base,
            employment_type=body.employment_type,
        )
    except InvalidRoleChangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alteração de papel não permitida",
        ) from exc
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        ) from exc


@router.post(
    "/invite",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Convida colaborador/admin por e-mail",
)
async def invite_user_endpoint(
    body: UserInviteRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
    redis: Redis = Depends(get_redis),
) -> User:
    try:
        user = await create_user(
            session,
            actor=principal,
            full_name=body.full_name,
            email=str(body.email),
            password=secrets.token_urlsafe(32),
            role=body.role,
            commission_percentage=body.commission_percentage,
            commission_fixed=body.commission_fixed,
            commission_base=body.commission_base,
            employment_type=body.employment_type,
        )
    except InvalidRoleChangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alteração de papel não permitida",
        ) from exc
    except EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado",
        ) from exc

    token = secrets.token_urlsafe(32)
    await redis.set(
        invite_key(principal.tenant_id, token),
        str(user.id),
        ex=7 * 24 * 60 * 60,
    )
    tenant = await session.get(Tenant, principal.tenant_id)
    tenant_slug = tenant.slug if tenant is not None else str(principal.tenant_id)
    link = (
        f"{settings.web_base_url}/aceitar-convite"
        f"?tenant={tenant_slug}&token={token}"
    )
    send_email(
        to=user.email,
        subject="Convite para a Sora Studio",
        body=(
            f"Olá, {user.full_name}.\n\n"
            f"Você foi convidado para a equipe. Defina sua senha em:\n"
            f"{link}\n\nO convite expira em 7 dias."
        ),
    )
    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Atualiza colaborador/admin (comissão, papel, status)",
)
async def update_user_endpoint(
    user_id: UUID,
    body: UserUpdateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
    redis: Redis = Depends(get_redis),
) -> User:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    changes = body.model_dump(exclude_unset=True)
    try:
        updated = await update_user(
            session,
            actor=principal,
            target=target,
            changes=changes,
        )
    except InvalidRoleChangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Alteração de papel não permitida",
        ) from exc

    if changes.get("is_active") is False:
        await revoke_all_sessions(
            redis,
            tenant_id=updated.tenant_id,
            user_id=updated.id,
        )

    return updated


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui usuário sem vínculos (não permite OWNER)",
)
async def delete_user_endpoint(
    user_id: UUID,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
    redis: Redis = Depends(get_redis),
) -> None:
    target = await session.get(User, user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    tenant_id = target.tenant_id
    try:
        await delete_user(session, actor=principal, target=target)
    except CannotDeleteUserError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário protegido não pode ser excluído",
        ) from exc
    except UserInUseError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Usuário possui vínculos e não pode ser excluído",
        ) from exc
    await revoke_all_sessions(
        redis,
        tenant_id=tenant_id,
        user_id=user_id,
    )


@router.get(
    "/me/commission",
    response_model=CommissionResponse,
    summary="Retorna a própria comissão",
)
async def my_commission(
    principal: Principal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_tenant_session),
) -> CommissionResponse:
    user = await session.get(User, principal.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    return CommissionResponse(
        user_id=user.id,
        commission_percentage=user.commission_percentage,
        commission_fixed=user.commission_fixed,
        commission_base=user.commission_base,
    )
