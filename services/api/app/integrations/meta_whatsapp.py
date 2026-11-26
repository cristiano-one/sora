"""Graph API mínima para o Embedded Signup (Tech Provider) da Meta.

As funções aqui nunca logam token nem payload de erro bruto. O token devolvido
pelo OAuth é de longa duração e fica cifrado no banco pela camada de serviço.
"""

import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15


class MetaWhatsAppError(Exception):
    """Falha controlada na comunicação com a Meta."""


@dataclass(frozen=True)
class MetaPhoneDetails:
    """Dados públicos do número retornados pela Graph API."""

    display_phone_number: str
    verified_name: str | None
    quality_rating: str | None


def _graph_url(path: str) -> str:
    version = settings.whatsapp_graph_version.strip("/")
    return f"https://graph.facebook.com/{version}/{path.lstrip('/')}"


def _json_object(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _graph_error_code(payload: dict[str, object]) -> str | None:
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    if isinstance(code, int | str):
        return str(code)
    return None


def _raise_graph_error(action: str, response: httpx.Response) -> None:
    payload = _json_object(response)
    code = _graph_error_code(payload)
    if code is None:
        logger.warning("Graph API %s falhou com HTTP %s", action, response.status_code)
    else:
        logger.warning(
            "Graph API %s falhou com HTTP %s (code=%s)",
            action,
            response.status_code,
            code,
        )
    raise MetaWhatsAppError(
        "A Meta recusou a operação. Confira a conta e tente novamente."
    )


async def exchange_code_for_token(code: str) -> str:
    """Troca o ``code`` do Embedded Signup por um access token da WABA."""
    if not settings.whatsapp_app_id or not settings.whatsapp_app_secret:
        raise MetaWhatsAppError(
            "Embedded Signup não configurado no servidor."
        )
    params = {
        "client_id": settings.whatsapp_app_id,
        "client_secret": settings.whatsapp_app_secret,
        "code": code,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(
                _graph_url("oauth/access_token"),
                params=params,
            )
    except httpx.HTTPError as exc:
        raise MetaWhatsAppError(
            "Não foi possível falar com a Meta. Tente novamente."
        ) from exc
    if not response.is_success:
        _raise_graph_error("oauth/access_token", response)
    payload = _json_object(response)
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise MetaWhatsAppError(
            "A Meta não retornou um token de acesso válido."
        )
    return token


async def subscribe_app_to_waba(waba_id: str, access_token: str) -> None:
    """Inscreve o app Sora no WABA para receber webhooks ``messages``."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                _graph_url(f"{waba_id}/subscribed_apps"),
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise MetaWhatsAppError(
            "Não foi possível falar com a Meta. Tente novamente."
        ) from exc
    if not response.is_success:
        _raise_graph_error("subscribed_apps", response)


async def unsubscribe_app_from_waba(waba_id: str, access_token: str) -> None:
    """Remove a inscrição do app no WABA (desconexão)."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.delete(
                _graph_url(f"{waba_id}/subscribed_apps"),
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise MetaWhatsAppError(
            "Não foi possível falar com a Meta. Tente novamente."
        ) from exc
    if not response.is_success:
        _raise_graph_error("subscribed_apps/delete", response)


async def register_phone_number(
    phone_number_id: str,
    access_token: str,
    pin: str,
) -> None:
    """Registra o número na Cloud API e define o PIN de duas etapas."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(
                _graph_url(f"{phone_number_id}/register"),
                headers={"Authorization": f"Bearer {access_token}"},
                json={"messaging_product": "whatsapp", "pin": pin},
            )
    except httpx.HTTPError as exc:
        raise MetaWhatsAppError(
            "Não foi possível falar com a Meta. Tente novamente."
        ) from exc
    if not response.is_success:
        _raise_graph_error("register", response)


async def fetch_phone_details(
    phone_number_id: str,
    access_token: str,
) -> MetaPhoneDetails:
    """Confirma o número e busca nome/qualidade exibidos pela Meta."""
    fields = "display_phone_number,verified_name,quality_rating,status"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(
                _graph_url(phone_number_id),
                params={"fields": fields},
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise MetaWhatsAppError(
            "Não foi possível falar com a Meta. Tente novamente."
        ) from exc
    if not response.is_success:
        _raise_graph_error("phone_number", response)
    payload = _json_object(response)
    display = payload.get("display_phone_number")
    if not isinstance(display, str) or not display:
        raise MetaWhatsAppError(
            "A Meta não retornou o número de telefone conectado."
        )
    verified_name = payload.get("verified_name")
    quality_rating = payload.get("quality_rating")
    return MetaPhoneDetails(
        display_phone_number=display,
        verified_name=(
            verified_name if isinstance(verified_name, str) else None
        ),
        quality_rating=(
            quality_rating if isinstance(quality_rating, str) else None
        ),
    )
