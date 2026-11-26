"""Cliente mínimo da Groq (API compatível com OpenAI Chat Completions)."""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GroqError(Exception):
    """Falha controlada na chamada à Groq."""


def _chat_url() -> str:
    return f"{settings.groq_base_url.rstrip('/')}/chat/completions"


def _json_object(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _raise_for_status(response: httpx.Response, model: str) -> None:
    if response.status_code in (401, 403):
        message = "Chave da Groq inválida ou revogada."
    elif response.status_code == 429:
        message = "Limite de uso da Groq atingido. Tente novamente em instantes."
    elif response.status_code == 400:
        message = "Modelo ou requisição inválida na Groq."
    else:
        message = "A Groq não conseguiu responder agora."
    logger.warning(
        "Groq recusou a chamada (HTTP %s, model=%s)",
        response.status_code,
        model,
    )
    raise GroqError(message)


async def chat_completion(
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.4,
    max_tokens: int = 500,
) -> str:
    """Executa uma completion e devolve somente o texto da primeira escolha."""
    if not api_key:
        raise GroqError("Chave da Groq não configurada.")
    try:
        async with httpx.AsyncClient(
            timeout=settings.groq_timeout_seconds
        ) as client:
            response = await client.post(
                _chat_url(),
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
    except httpx.HTTPError as exc:
        raise GroqError(
            "Não foi possível falar com a Groq. Tente novamente."
        ) from exc

    if not response.is_success:
        _raise_for_status(response, model)

    payload = _json_object(response)
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise GroqError("A Groq não retornou uma resposta.")
    first = choices[0]
    if not isinstance(first, dict):
        raise GroqError("A Groq retornou uma resposta inválida.")
    message = first.get("message")
    if not isinstance(message, dict):
        raise GroqError("A Groq retornou uma resposta inválida.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise GroqError("A Groq retornou uma resposta vazia.")
    return content.strip()
