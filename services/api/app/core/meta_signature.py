"""Validação de assinatura e token do webhook oficial da Meta."""

import hashlib
import hmac


def verify_meta_signature(
    *,
    raw_body: bytes,
    signature_header: str,
    app_secret: str,
) -> bool:
    """Valida ``X-Hub-Signature-256`` em tempo constante.

    Falha fechada quando o segredo do app não está configurado.
    """
    if not app_secret or not signature_header.startswith("sha256="):
        return False
    provided = signature_header.removeprefix("sha256=")
    expected = hmac.new(
        app_secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(provided, expected)


def verify_meta_verify_token(provided: str, expected: str) -> bool:
    """Compara o token de verificação do webhook em tempo constante."""
    if not expected:
        return False
    return hmac.compare_digest(provided, expected)
