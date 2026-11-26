"""Hash de senha (Argon2) e emissão/validação de tokens JWT."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import jwt
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.redis import tenant_key
from app.models.user import UserRole

_password_hasher = PasswordHash.recommended()

# Hash Argon2 fixo de uma senha descartável (não é segredo). Usado para
# equalizar o tempo de resposta quando o tenant/usuário não existe.
_DUMMY_ARGON2_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$igl6NnjZRt39UyU3vxLHDQ$"
    "9m+jpoXypJEGXd4bJiOYx5RcQCm0bAvX9yydzL3Llvw"
)


class TokenType(StrEnum):
    """Tipos de token emitidos pela API."""

    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Token ausente, inválido, expirado ou de tipo inesperado."""


@dataclass(frozen=True)
class TokenPayload:
    """Claims validadas de um token Sora."""

    user_id: uuid.UUID
    tenant_id: uuid.UUID
    role: UserRole
    token_type: TokenType
    jti: str
    issued_at: datetime
    issued_at_ms: int
    expires_at: datetime


def hash_password(password: str) -> str:
    """Gera o hash Argon2 da senha."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Compara a senha com o hash, retornando False em qualquer falha."""
    try:
        return _password_hasher.verify(password, hashed_password)
    except Exception:
        return False


def verify_dummy_password(password: str) -> None:
    """Executa um verify descartável para mitigar enumeração por timing."""
    verify_password(password, _DUMMY_ARGON2_HASH)


def _create_token(
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: UserRole,
    token_type: TokenType,
    expires_delta: timedelta,
) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + expires_delta
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role.value,
        "type": token_type.value,
        "jti": jti,
        "iat": now,
        "iat_ms": int(now.timestamp() * 1000),
        "exp": expires_at,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: UserRole,
) -> tuple[str, str, datetime]:
    """Emite um access token de curta duração."""
    return _create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: UserRole,
) -> tuple[str, str, datetime]:
    """Emite um refresh token de longa duração (rotativo no Redis)."""
    return _create_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str, *, expected_type: TokenType) -> TokenPayload:
    """Valida assinatura, emissor, audiência, expiração e tipo do token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={
                "require": [
                    "exp",
                    "iat",
                    "iat_ms",
                    "sub",
                    "jti",
                    "type",
                    "tenant_id",
                    "role",
                ]
            },
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError

    try:
        return TokenPayload(
            user_id=uuid.UUID(payload["sub"]),
            tenant_id=uuid.UUID(payload["tenant_id"]),
            role=UserRole(payload["role"]),
            token_type=expected_type,
            jti=str(payload["jti"]),
            issued_at=datetime.fromtimestamp(int(payload["iat"]), tz=UTC),
            issued_at_ms=int(payload["iat_ms"]),
            expires_at=datetime.fromtimestamp(int(payload["exp"]), tz=UTC),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError from exc


def refresh_key(tenant_id: uuid.UUID, jti: str) -> str:
    """Chave Redis do refresh token (rotativo)."""
    return tenant_key(tenant_id, "auth", "refresh", jti)


def denylist_key(tenant_id: uuid.UUID, jti: str) -> str:
    """Chave Redis da denylist de access tokens (logout)."""
    return tenant_key(tenant_id, "auth", "denylist", jti)


def revoked_at_key(tenant_id: uuid.UUID, user_id: uuid.UUID) -> str:
    """Chave Redis do instante de revogação em massa do usuário."""
    return tenant_key(tenant_id, "auth", "revoked_at", str(user_id))


def password_reset_key(tenant_id: uuid.UUID, token: str) -> str:
    """Chave Redis do token de recuperação de senha."""
    return tenant_key(tenant_id, "auth", "password_reset", token)


def invite_key(tenant_id: uuid.UUID, token: str) -> str:
    """Chave Redis do convite de colaborador."""
    return tenant_key(tenant_id, "auth", "invite", token)
