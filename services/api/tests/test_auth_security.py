"""Testes unitários de hash de senha e JWT."""

from uuid import uuid4

import pytest
from app.core.auth.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    denylist_key,
    hash_password,
    refresh_key,
    revoked_at_key,
    verify_password,
)
from app.core.config import settings
from app.models.user import UserRole


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("senha-forte-123")

    assert hashed != "senha-forte-123"
    assert verify_password("senha-forte-123", hashed) is True
    assert verify_password("senha-errada", hashed) is False


def test_access_token_roundtrip() -> None:
    user_id = uuid4()
    tenant_id = uuid4()

    token, jti, _ = create_access_token(user_id, tenant_id, UserRole.OWNER)
    payload = decode_token(token, expected_type=TokenType.ACCESS)

    assert payload.user_id == user_id
    assert payload.tenant_id == tenant_id
    assert payload.role is UserRole.OWNER
    assert payload.jti == jti


def test_refresh_token_is_not_accepted_as_access() -> None:
    token, _, _ = create_refresh_token(uuid4(), uuid4(), UserRole.ADMIN)

    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_tampered_token_is_rejected() -> None:
    token, _, _ = create_access_token(uuid4(), uuid4(), UserRole.OWNER)

    with pytest.raises(InvalidTokenError):
        decode_token(f"{token}x", expected_type=TokenType.ACCESS)


def test_expired_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_access_token_expire_minutes", -1)
    token, _, _ = create_access_token(uuid4(), uuid4(), UserRole.OWNER)

    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_token_signed_with_other_secret_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token, _, _ = create_access_token(uuid4(), uuid4(), UserRole.OWNER)
    monkeypatch.setattr(settings, "jwt_secret_key", "outro-segredo-com-no-minimo-32-bytes")

    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type=TokenType.ACCESS)


def test_redis_keys_are_tenant_prefixed() -> None:
    tenant_id = uuid4()
    user_id = uuid4()

    assert refresh_key(tenant_id, "abc").startswith(f"tenant:{tenant_id}:")
    assert denylist_key(tenant_id, "abc").startswith(f"tenant:{tenant_id}:")
    assert revoked_at_key(tenant_id, user_id).startswith(f"tenant:{tenant_id}:")
