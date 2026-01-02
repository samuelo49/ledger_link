from __future__ import annotations

import logging
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt

from .settings import wallet_settings
from shared import JWKSClient

logger = logging.getLogger(__name__)

ACCEPTED_SCOPES = {"access", "wallet_access"}
jwks_client = JWKSClient(wallet_settings().jwks_url, cache_ttl=300)


def get_current_user_id(request: Request) -> int:
    """Extract and validate the current user's numeric ID from a JWT bearer token.

    Hardening improvements:
    * Accept multiple access scopes defined in ACCEPTED_SCOPES.
    * Provide structured logging of token decode failures (internal visibility).
    * Explicitly check presence of 'sub' claim and differentiate unsupported format.
    * Lays groundwork for future UUID subjects by failing fast with a clear message.

    Migration path for UUID subjects (future):
    1. Introduce parallel string column (e.g. principal_id) on domain entities.
    2. Populate both numeric user_id (if convertible) and principal_id.
    3. Gradually switch lookups to principal_id; then backfill and drop numeric user_id.
    4. Update this dependency to return raw subject while separate helper provides int when available.
    """
    settings = wallet_settings()
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        logger.warning("wallet.auth.invalid_header", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing key identifier")
    try:
        public_key = jwks_client.get_key(kid)
    except Exception as exc:  # noqa: BLE001
        logger.error("wallet.auth.jwks_fetch_failed", extra={"error": str(exc)})
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
        logger.warning("wallet.auth.jwt_decode_failed", extra={"error": str(exc)})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    scope = decoded.get("scope")
    if scope not in ACCEPTED_SCOPES:
        logger.info("wallet.auth.scope_rejected", extra={"scope": scope})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope")

    sub = decoded.get("sub")
    if sub is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing subject")

    if isinstance(sub, str) and sub.isdigit():
        return int(sub)

    # Future: support UUID or non-numeric subjects via separate dependency.
    logger.info("wallet.auth.unsupported_subject_format", extra={"subject": sub})
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unsupported subject format (expected numeric)")
