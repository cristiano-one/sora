"""Autenticação de endpoints internos (roteador WhatsApp, workers)."""

import hmac

from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_internal_token(
    x_internal_token: str = Header(default=""),
) -> None:
    """Compara o token compartilhado em tempo constante."""
    if not hmac.compare_digest(x_internal_token, settings.internal_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não autorizado",
        )
