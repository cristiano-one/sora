"""Endpoints internos de assinaturas de clientes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.subscriptions import (
    ClientSubscriptionCreateRequest,
    ClientSubscriptionResponse,
)
from app.core.auth.dependencies import (
    Principal,
    get_tenant_session,
    require_roles,
)
from app.models import (
    Client,
    ClientSubscription,
    ClientSubscriptionStatus,
    UserRole,
)
from app.modules.subscriptions.service import (
    SubscriptionConflictError,
    SubscriptionNotFoundError,
    cancel_client_subscription,
    create_client_subscription,
    delete_client_subscription,
    list_client_subscriptions,
    subscription_response,
)

router = APIRouter(tags=["subscriptions"])

_require_manager = require_roles(UserRole.OWNER, UserRole.ADMIN)


async def _get_client(session: AsyncSession, client_id: UUID) -> Client:
    client = await session.get(Client, client_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado",
        )
    return client


async def _get_subscription(
    session: AsyncSession,
    subscription_id: UUID,
) -> ClientSubscription:
    subscription = await session.get(ClientSubscription, subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assinatura não encontrada",
        )
    return subscription


@router.get(
    "/subscriptions",
    response_model=list[ClientSubscriptionResponse],
    summary="Lista assinaturas do tenant",
)
async def list_subscriptions_endpoint(
    client_id: UUID | None = Query(default=None),
    subscription_status: ClientSubscriptionStatus | None = Query(
        default=None,
        alias="status",
    ),
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[ClientSubscriptionResponse]:
    subscriptions = await list_client_subscriptions(
        session,
        client_id=client_id,
        status=subscription_status,
    )
    return [
        await subscription_response(session, subscription)
        for subscription in subscriptions
    ]


@router.get(
    "/clients/{client_id}/subscriptions",
    response_model=list[ClientSubscriptionResponse],
    summary="Lista assinaturas de um cliente",
)
async def list_client_subscriptions_endpoint(
    client_id: UUID,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> list[ClientSubscriptionResponse]:
    await _get_client(session, client_id)
    subscriptions = await list_client_subscriptions(
        session,
        client_id=client_id,
    )
    return [
        await subscription_response(session, subscription)
        for subscription in subscriptions
    ]


@router.post(
    "/clients/{client_id}/subscriptions",
    response_model=ClientSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Contrata plano para um cliente",
)
async def create_client_subscription_endpoint(
    client_id: UUID,
    body: ClientSubscriptionCreateRequest,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> ClientSubscriptionResponse:
    client = await _get_client(session, client_id)
    try:
        subscription = await create_client_subscription(
            session,
            tenant_id=principal.tenant_id,
            client=client,
            plan_id=body.plan_id,
            status=ClientSubscriptionStatus.ACTIVE,
        )
    except SubscriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plano não encontrado",
        ) from exc
    except SubscriptionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cliente já possui assinatura ativa",
        ) from exc
    return await subscription_response(session, subscription)


@router.post(
    "/subscriptions/{subscription_id}/cancel",
    response_model=ClientSubscriptionResponse,
    summary="Cancela uma assinatura",
)
async def cancel_subscription_endpoint(
    subscription_id: UUID,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> ClientSubscriptionResponse:
    subscription = await _get_subscription(session, subscription_id)
    try:
        subscription = await cancel_client_subscription(session, subscription)
    except SubscriptionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assinatura já encerrada",
        ) from exc
    return await subscription_response(session, subscription)


@router.delete(
    "/subscriptions/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui assinatura cancelada/expirada",
)
async def delete_subscription_endpoint(
    subscription_id: UUID,
    principal: Principal = Depends(_require_manager),
    session: AsyncSession = Depends(get_tenant_session),
) -> None:
    subscription = await _get_subscription(session, subscription_id)
    try:
        await delete_client_subscription(session, subscription)
    except SubscriptionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancele a assinatura antes de excluí-la",
        ) from exc
