"""Endpoints públicos de link mágico e agendamento (sem login)."""

import hmac
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.agenda import AvailabilityResponse
from app.api.schemas.payments import PublicPaymentConfirmResponse
from app.api.schemas.public_booking import (
    MagicLinkRequest,
    MagicLinkResponse,
    PublicAppointmentCreateRequest,
    PublicAppointmentResponse,
    PublicContextResponse,
)
from app.api.schemas.subscriptions import (
    PublicSubscriptionCreateRequest,
    PublicSubscriptionResponse,
)
from app.core.config import settings
from app.core.redis import get_redis
from app.db.session import get_session
from app.modules.agenda.public_service import (
    InvalidMagicLinkError,
    PaymentNotFoundError,
    PublicBookingConflictError,
    PublicBookingError,
    PublicTenantNotFoundError,
    create_magic_link,
    get_public_context,
    public_availability,
    public_confirm_mock_payment,
    public_create_appointment,
    public_create_subscription,
    public_get_payment,
)
from app.modules.agenda.service import (
    AgendaBusyError,
    InvalidAppointmentError,
    QuotaUnavailableError,
    SlotUnavailableError,
)

router = APIRouter(prefix="/public", tags=["public-booking"])


def _verify_internal(x_internal_token: str = Header(default="")) -> None:
    if not hmac.compare_digest(x_internal_token, settings.internal_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autorizado",
        )


def _map_public_error(exc: Exception) -> HTTPException:
    if isinstance(exc, InvalidMagicLinkError):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Link inválido ou expirado",
        )
    if isinstance(exc, PublicTenantNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clínica não encontrada",
        )
    if isinstance(exc, PaymentNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pagamento não encontrado",
        )
    if isinstance(exc, PublicBookingConflictError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    if isinstance(exc, (AgendaBusyError, SlotUnavailableError)):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Horário indisponível",
        )
    if isinstance(exc, QuotaUnavailableError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cota do plano indisponível",
        )
    if isinstance(exc, (PublicBookingError, InvalidAppointmentError)):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Não foi possível concluir o agendamento",
    )


@router.post(
    "/{slug}/magic-link",
    response_model=MagicLinkResponse,
    dependencies=[Depends(_verify_internal)],
    summary="Gera link mágico para o WhatsApp (interno)",
)
async def create_magic_link_endpoint(
    slug: str,
    body: MagicLinkRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> MagicLinkResponse:
    try:
        return await create_magic_link(
            session,
            redis,
            slug=slug,
            phone=body.phone,
        )
    except (PublicTenantNotFoundError, PublicBookingError) as exc:
        raise _map_public_error(exc) from exc


@router.get(
    "/{slug}/context",
    response_model=PublicContextResponse,
    summary="Contexto público do link (clínica, serviços e profissionais)",
)
async def public_context_endpoint(
    slug: str,
    t: str = Query(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PublicContextResponse:
    try:
        return await get_public_context(
            session,
            redis,
            slug=slug,
            token=t,
        )
    except (
        InvalidMagicLinkError,
        PublicTenantNotFoundError,
        PublicBookingError,
    ) as exc:
        raise _map_public_error(exc) from exc


@router.get(
    "/{slug}/availability",
    response_model=AvailabilityResponse,
    summary="Disponibilidade pública (somente horários livres)",
)
async def public_availability_endpoint(
    slug: str,
    t: str = Query(...),
    service_id: UUID = Query(...),
    collaborator_id: UUID = Query(...),
    day: date = Query(..., alias="date"),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> AvailabilityResponse:
    try:
        return await public_availability(
            session,
            redis,
            slug=slug,
            token=t,
            service_id=service_id,
            collaborator_id=collaborator_id,
            day=day,
        )
    except (
        InvalidMagicLinkError,
        PublicTenantNotFoundError,
        PublicBookingError,
        InvalidAppointmentError,
    ) as exc:
        raise _map_public_error(exc) from exc


@router.post(
    "/{slug}/subscriptions",
    response_model=PublicSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Contrata plano de assinatura pelo link mágico",
)
async def public_create_subscription_endpoint(
    slug: str,
    body: PublicSubscriptionCreateRequest,
    t: str = Query(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PublicSubscriptionResponse:
    try:
        return await public_create_subscription(
            session,
            redis,
            slug=slug,
            token=t,
            plan_id=body.plan_id,
            full_name=body.full_name,
        )
    except (
        InvalidMagicLinkError,
        PublicTenantNotFoundError,
        PublicBookingError,
        PublicBookingConflictError,
    ) as exc:
        raise _map_public_error(exc) from exc


@router.get(
    "/{slug}/payments/{payment_id}",
    response_model=PublicPaymentConfirmResponse,
    summary="Consulta o status do próprio pagamento Pix",
)
async def public_payment_status_endpoint(
    slug: str,
    payment_id: UUID,
    t: str = Query(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PublicPaymentConfirmResponse:
    try:
        return await public_get_payment(
            session,
            redis,
            slug=slug,
            token=t,
            payment_id=payment_id,
        )
    except (
        InvalidMagicLinkError,
        PublicTenantNotFoundError,
        PublicBookingError,
        PaymentNotFoundError,
    ) as exc:
        raise _map_public_error(exc) from exc


@router.post(
    "/{slug}/payments/{payment_id}/mock-confirm",
    response_model=PublicPaymentConfirmResponse,
    summary="Confirma o Pix no provider mock (somente dev)",
)
async def public_payment_mock_confirm_endpoint(
    slug: str,
    payment_id: UUID,
    t: str = Query(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PublicPaymentConfirmResponse:
    try:
        return await public_confirm_mock_payment(
            session,
            redis,
            slug=slug,
            token=t,
            payment_id=payment_id,
        )
    except (
        InvalidMagicLinkError,
        PublicTenantNotFoundError,
        PublicBookingError,
        PublicBookingConflictError,
        PaymentNotFoundError,
    ) as exc:
        raise _map_public_error(exc) from exc


@router.post(
    "/{slug}/appointments",
    response_model=PublicAppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Agendamento público via link mágico",
)
async def public_create_appointment_endpoint(
    slug: str,
    body: PublicAppointmentCreateRequest,
    t: str = Query(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> PublicAppointmentResponse:
    try:
        return await public_create_appointment(
            session,
            redis,
            slug=slug,
            token=t,
            service_id=body.service_id,
            collaborator_id=body.collaborator_id,
            starts_at=body.starts_at,
            full_name=body.full_name,
        )
    except (
        InvalidMagicLinkError,
        PublicTenantNotFoundError,
        PublicBookingError,
        PublicBookingConflictError,
        InvalidAppointmentError,
        AgendaBusyError,
        QuotaUnavailableError,
        SlotUnavailableError,
    ) as exc:
        raise _map_public_error(exc) from exc
