"""Envio de mensagens WhatsApp (mock, número global ou conta do tenant)."""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WhatsAppCredentials:
    """Credenciais da WABA/número conectado pela própria clínica."""

    phone_number_id: str
    access_token: str


def _graph_url(path: str) -> str:
    version = settings.whatsapp_graph_version.strip("/")
    return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"


async def _send_with_credentials(
    *,
    phone: str,
    text: str,
    credentials: WhatsAppCredentials,
) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                _graph_url(f"{credentials.phone_number_id}/messages"),
                headers={
                    "Authorization": f"Bearer {credentials.access_token}",
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": text},
                },
            )
        if not response.is_success:
            logger.warning(
                "Meta recusou envio WhatsApp (HTTP %s)",
                response.status_code,
            )
        return response.is_success
    except httpx.HTTPError:
        logger.warning("Falha de rede ao enviar mensagem WhatsApp")
        return False


async def send_whatsapp_message(
    *,
    phone: str,
    text: str,
    credentials: WhatsAppCredentials | None = None,
) -> bool:
    """Envia a mensagem pelo provider configurado, sem logar conteúdo/PII.

    Quando a clínica conectou o próprio número (Tech Provider), as
    ``credentials`` têm prioridade e a cobrança da Meta fica na conta dela.
    Sem credenciais, mantém o mock ou o número global de desenvolvimento.
    """
    if credentials is not None:
        return await _send_with_credentials(
            phone=phone,
            text=text,
            credentials=credentials,
        )

    provider = settings.whatsapp_provider.lower()
    if provider == "mock":
        return True
    if provider != "meta":
        logger.warning("WhatsApp provider desconhecido: %s", provider)
        return False

    token = settings.whatsapp_meta_token
    phone_number_id = settings.whatsapp_meta_phone_number_id
    if not token or not phone_number_id:
        logger.warning("WhatsApp Meta sem token/phone_number_id configurados")
        return False

    return await _send_with_credentials(
        phone=phone,
        text=text,
        credentials=WhatsAppCredentials(
            phone_number_id=phone_number_id,
            access_token=token,
        ),
    )
