"""Testes unitários de criptografia e mascaramento."""

from app.core.crypto import decrypt_text, encrypt_text
from app.core.formatting import mask_phone


def test_encrypt_decrypt_roundtrip() -> None:
    secret = "cliente teve reação alérgica"
    encrypted = encrypt_text(secret)

    assert encrypted != secret
    assert decrypt_text(encrypted) == secret


def test_encrypt_is_nondeterministic() -> None:
    secret = "mesma nota"

    assert encrypt_text(secret) != encrypt_text(secret)


def test_mask_phone_mobile() -> None:
    assert mask_phone("(11) 91234-5678") == "(11) 9****-5678"


def test_mask_phone_landline() -> None:
    assert mask_phone("(11) 3456-7890") == "(11) ****-7890"


def test_mask_phone_invalid() -> None:
    assert mask_phone("123") == "***"
