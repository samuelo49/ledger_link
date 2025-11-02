from __future__ import annotations

"""Identity proxy routes for the API Gateway.

This module exposes the public auth endpoints under 
``/api/v1/auth`` and forwards them to the Identity service. The gateway 
remains a thin pass-through: it copies safe headers, preserves method/body, 
and returns the upstream status and content type. Business logic and 
authentication validation reside in the Identity service.

Proxied routes:
- POST /register -> identity /auth/register
- POST /token -> identity /auth/token
- POST /refresh -> identity /auth/refresh
- GET  /me -> identity /auth/me
- POST /verification/request -> identity /auth/verification/request
- POST /verification/confirm -> identity /auth/verification/confirm
- POST /password-reset/request -> identity /auth/password-reset/request
- POST /password-reset/confirm -> identity /auth/password-reset/confirm
"""

from typing import Iterable

import httpx
from fastapi import APIRouter, Request, Response

from ..settings import gateway_settings

router = APIRouter(prefix="/api/v1/auth")


HOP_BY_HOP_HEADERS: set[str] = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def _forward_headers(request: Request, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Return a sanitized copy of incoming headers suitable for proxying.

    Drops hop-by-hop headers and forwards a small allowlist of safe headers.
    Optionally merges additional header key/values from ``extra``.
    """
    headers: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        # Only forward selected headers for safety; add more if needed
        if lk in {"authorization", "content-type", "accept", "x-request-id"}:
            headers[k] = v
    if extra:
        headers.update(extra)
    return headers


async def _proxy_post(path: str, request: Request) -> Response:
    """Forward a POST request body and headers to the Identity service."""
    settings = gateway_settings()
    url = f"{settings.identity_base_url}{path}"
    body = await request.body()
    headers = _forward_headers(request)
    timeout = httpx.Timeout(10.0, read=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream = await client.post(url, content=body, headers=headers)
    # Build response
    content_type = upstream.headers.get("content-type")
    response_headers = _select_response_headers(upstream.headers)
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=content_type, headers=response_headers)


async def _proxy_get(path: str, request: Request) -> Response:
    """Forward a GET request with query params and headers to Identity."""
    settings = gateway_settings()
    url = f"{settings.identity_base_url}{path}"
    headers = _forward_headers(request)
    timeout = httpx.Timeout(10.0, read=20.0)
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream = await client.get(url, headers=headers, params=params)
    content_type = upstream.headers.get("content-type")
    response_headers = _select_response_headers(upstream.headers)
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=content_type, headers=response_headers)


def _select_response_headers(headers: httpx.Headers | dict[str, str] | Iterable[tuple[str, str]]) -> dict[str, str]:
    """Filter upstream response headers to a safe subset for clients."""
    out: dict[str, str] = {}
    if isinstance(headers, httpx.Headers):
        items = headers.items()
    elif isinstance(headers, dict):
        items = headers.items()
    else:
        items = headers
    for k, v in items:
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        if lk in {"content-type", "cache-control", "etag", "vary", "x-request-id"}:
            out[k] = v
    return out


@router.post("/register")
async def register(request: Request) -> Response:
    """Create a new account by proxying to Identity."""
    return await _proxy_post("/auth/register", request)


@router.post("/token")
async def token(request: Request) -> Response:
    """Issue access/refresh tokens by proxying to Identity."""
    return await _proxy_post("/auth/token", request)


@router.post("/refresh")
async def refresh(request: Request) -> Response:
    """Exchange a refresh token for a new access token (proxy)."""
    return await _proxy_post("/auth/refresh", request)


@router.get("/me")
async def me(request: Request) -> Response:
    """Return the current authenticated user (proxy)."""
    return await _proxy_get("/auth/me", request)


@router.post("/verification/request")
async def verification_request(request: Request) -> Response:
    """Request a verification token/email (proxy)."""
    return await _proxy_post("/auth/verification/request", request)


@router.post("/verification/confirm")
async def verification_confirm(request: Request) -> Response:
    """Confirm account verification using a token (proxy)."""
    return await _proxy_post("/auth/verification/confirm", request)


@router.post("/password-reset/request")
async def password_reset_request(request: Request) -> Response:
    """Request a password reset token (proxy)."""
    return await _proxy_post("/auth/password-reset/request", request)


@router.post("/password-reset/confirm")
async def password_reset_confirm(request: Request) -> Response:
    """Confirm a password reset using a token (proxy)."""
    return await _proxy_post("/auth/password-reset/confirm", request)
