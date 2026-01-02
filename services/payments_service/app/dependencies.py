from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from jose import jwt, JWTError

from shared import JWKSClient

from .settings import payments_settings

jwks_client = JWKSClient(payments_settings().jwks_url, cache_ttl=300)


def get_current_user_id(request: Request) -> int:
    settings = payments_settings()
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header") from exc
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing key identifier")
    try:
        public_key = jwks_client.get_key(kid)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to validate token (JWKS fetch failed)",
        ) from exc
    try:
        decoded = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if decoded.get("scope") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope")
    try:
        return int(decoded["sub"])
    except (KeyError, ValueError):  # noqa: PERF203
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")


CurrentUserIdDep = Depends(get_current_user_id)
