"""Conexão WhatsApp Business por tenant (modelo Tech Provider)."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_text, encrypt_text
from app.core.whatsapp import WhatsAppCredentials
from app.integrations.meta_whatsapp import (
    MetaWhatsAppError,
    exchange_code_for_token,
    fetch_phone_details,
    register_phone_number,
    subscribe_app_to_waba,
    unsubscribe_app_from_waba,
)
from app.models import (
    TenantWhatsAppAccount,
    WhatsAppConnectionStatus,
    WhatsAppRegistrationStatus,
)

logger = logging.getLogger(__name__)


class WhatsAppAlreadyConnectedError(Exception):
    """Número já vinculado a outra clínica."""


class WhatsAppConnectionNotFoundError(Exception):
    """Clínica ainda não possui conexão WhatsApp."""


async def resolve_tenant_id_by_phone_number_id(
    session: AsyncSession,
    phone_number_id: str,
) -> UUID | None:
    """Resolve o tenant de um webhook sem JWT (função SECURITY DEFINER)."""
    value = await session.scalar(
        text("SELECT public.resolve_tenant_id_by_whatsapp_phone(:phone)"),
        {"phone": phone_number_id},
    )
    if value is None:
        return None
    return value if isinstance(value, UUID) else UUID(str(value))


async def get_account(
    session: AsyncSession,
    tenant_id: UUID,
) -> TenantWhatsAppAccount | None:
    """Busca a conexão do tenant atual (RLS aplicada)."""
    return await session.get(TenantWhatsAppAccount, tenant_id)


async def get_credentials_for_tenant(
    session: AsyncSession,
    tenant_id: UUID,
) -> WhatsAppCredentials | None:
    """Decifra o token da clínica; falha fechada se a conexão for inválida."""
    account = await session.get(TenantWhatsAppAccount, tenant_id)
    if (
        account is None
        or account.status is not WhatsAppConnectionStatus.CONNECTED
        or not account.phone_number_id
        or not account.access_token_encrypted
    ):
        return None
    try:
        token = decrypt_text(account.access_token_encrypted)
    except ValueError:
        logger.error("Token WhatsApp inválido para o tenant %s", tenant_id)
        return None
    return WhatsAppCredentials(
        phone_number_id=account.phone_number_id,
        access_token=token,
    )


async def connect_tenant(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    actor_user_id: UUID,
    code: str,
    waba_id: str,
    phone_number_id: str,
    pin: str,
) -> TenantWhatsAppAccount:
    """Valida o Embedded Signup na Meta e salva a conexão cifrada.

    A ordem importa: só gravamos no banco depois de trocar o code, inscrever o
    app no WABA, confirmar o número e tentar registrá-lo na Cloud API. Falha de
    registro (por exemplo, número já registrado) não descarta a conexão; ela é
    exposta no estado para o gestor decidir se reconecta.
    """
    owner_tenant = await resolve_tenant_id_by_phone_number_id(
        session,
        phone_number_id,
    )
    if owner_tenant is not None and owner_tenant != tenant_id:
        raise WhatsAppAlreadyConnectedError

    token = await exchange_code_for_token(code)
    subscribed = False
    try:
        await subscribe_app_to_waba(waba_id, token)
        subscribed = True
        details = await fetch_phone_details(phone_number_id, token)
    except MetaWhatsAppError:
        if subscribed:
            try:
                await unsubscribe_app_from_waba(waba_id, token)
            except MetaWhatsAppError:
                logger.warning("Falha ao desfazer inscrição após erro de conexão")
        raise

    now = datetime.now(UTC)
    registration_status = WhatsAppRegistrationStatus.REGISTERED
    registration_error: str | None = None
    registered_at: datetime | None = now
    try:
        await register_phone_number(phone_number_id, token, pin)
    except MetaWhatsAppError as exc:
        registration_status = WhatsAppRegistrationStatus.FAILED
        registration_error = (
            f"Registro na Cloud API não confirmado: {exc}"
        )[:500]
        registered_at = None

    account = await session.get(TenantWhatsAppAccount, tenant_id)
    if account is None:
        account = TenantWhatsAppAccount(tenant_id=tenant_id)
        session.add(account)
    account.status = WhatsAppConnectionStatus.CONNECTED
    account.waba_id = waba_id
    account.phone_number_id = phone_number_id
    account.display_phone_number = details.display_phone_number
    account.verified_name = details.verified_name
    account.quality_rating = details.quality_rating
    account.access_token_encrypted = encrypt_text(token)
    account.registration_status = registration_status
    account.registration_error = registration_error
    account.registration_pin_encrypted = (
        encrypt_text(pin)
        if registration_status is WhatsAppRegistrationStatus.REGISTERED
        else None
    )
    account.registered_at = registered_at
    account.connected_at = now
    account.connected_by = actor_user_id
    account.last_error = None

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        try:
            await unsubscribe_app_from_waba(waba_id, token)
        except MetaWhatsAppError:
            logger.warning("Falha ao desfazer inscrição após conflito de número")
        raise WhatsAppAlreadyConnectedError from exc

    return account


async def disconnect_tenant(
    session: AsyncSession,
    *,
    tenant_id: UUID,
) -> TenantWhatsAppAccount:
    """Remove a inscrição na Meta (best effort) e apaga as credenciais locais."""
    account = await session.get(TenantWhatsAppAccount, tenant_id)
    if account is None:
        raise WhatsAppConnectionNotFoundError

    credentials = await get_credentials_for_tenant(session, tenant_id)
    if credentials is not None and account.waba_id:
        try:
            await unsubscribe_app_from_waba(
                account.waba_id,
                credentials.access_token,
            )
        except MetaWhatsAppError:
            logger.warning(
                "Falha ao remover inscrição do WhatsApp na Meta; "
                "credenciais locais serão apagadas"
            )

    account.status = WhatsAppConnectionStatus.DISCONNECTED
    account.waba_id = None
    account.phone_number_id = None
    account.access_token_encrypted = None
    account.registration_status = WhatsAppRegistrationStatus.PENDING
    account.registration_error = None
    account.registration_pin_encrypted = None
    account.registered_at = None
    account.connected_at = None
    account.connected_by = None
    account.last_error = None
    await session.commit()
    return account
