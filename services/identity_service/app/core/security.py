from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from ..settings import identity_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(subject: str, scope: str, expires_delta: timedelta, *, token_type: str) -> str:
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
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)
