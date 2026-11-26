"""Envio de mensagens WhatsApp (mock ou Meta Cloud API)."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/v22.0"


async def send_whatsapp_message(*, phone: str, text: str) -> bool:
    """Envia a mensagem pelo provider configurado, sem logar conteúdo/PII."""
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

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{META_GRAPH_URL}/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": text},
                },
            )
        return response.is_success
    except httpx.HTTPError:
        logger.warning("Falha de rede ao enviar mensagem WhatsApp")
        return False
