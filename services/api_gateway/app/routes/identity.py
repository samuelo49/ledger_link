from __future__ import annotations

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


def _select_response_headers(headers: httpx.Headers | dict[str, str] | Iterable[tuple[str, str]]) -> dict[str, str]:
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
    return await _proxy_post("/auth/register", request)


@router.post("/token")
async def token(request: Request) -> Response:
    return await _proxy_post("/auth/token", request)


@router.post("/refresh")
async def refresh(request: Request) -> Response:
    return await _proxy_post("/auth/refresh", request)
