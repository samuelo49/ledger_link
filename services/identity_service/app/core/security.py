from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..settings import identity_settings
from .keys import get_private_key, get_public_key

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(
    subject: str,
    scope: str,
    expires_delta: timedelta,
    *,
    token_type: str,
    jti: str | None = None,
) -> str:
    settings = identity_settings()
    now = datetime.now(tz=timezone.utc)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "scope": scope,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "typ": token_type,
        "jti": jti or str(uuid4()),
    }
    headers = {"kid": settings.jwt_key_id}
    return jwt.encode(payload, get_private_key(), algorithm="RS256", headers=headers)


def decode_token(token: str, *, expected_scope: str | None = None, token_type: str | None = None) -> dict[str, Any]:
    """Decode a JWT access/refresh token using the configured RSA public key."""
    settings = identity_settings()
    decoded = jwt.decode(
        token,
        get_public_key(),
        algorithms=["RS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    if expected_scope and decoded.get("scope") != expected_scope:
        raise JWTError("Invalid token scope")
    if token_type and decoded.get("typ") != token_type:
        raise JWTError("Invalid token type")
    return decoded


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
