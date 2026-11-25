"""Criptografia de colunas sensíveis (Fernet derivado da ENCRYPTION_KEY)."""

from base64 import urlsafe_b64encode
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    key = urlsafe_b64encode(sha256(settings.encryption_key.encode()).digest())
    return Fernet(key)


def encrypt_text(value: str) -> str:
    """Cifra um texto sensível para armazenamento em coluna."""
    return _fernet().encrypt(value.encode()).decode()


def decrypt_text(value: str) -> str:
    """Decifra um texto; falha fechada em caso de chave/conteúdo inválido."""
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Conteúdo criptográfico inválido") from exc
