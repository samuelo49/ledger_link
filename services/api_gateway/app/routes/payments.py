from __future__ import annotations

"""Payments proxy routes for the API Gateway.

Exposes payment intent endpoints under ``/api/v1/payments`` and forwards to the
Payments service. Orchestration, risk decisions, and wallet debits are handled
downstream; the gateway simply forwards requests and returns responses.
"""

from typing import Iterable

import httpx
from fastapi import APIRouter, Request, Response

from ..settings import gateway_settings

router = APIRouter(prefix="/api/v1/payments")


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
    """Return a sanitized copy of incoming headers suitable for proxying."""
    headers: dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk in HOP_BY_HOP_HEADERS:
            continue
        if lk in {"authorization", "content-type", "accept", "x-request-id"}:
            headers[k] = v
    if extra:
        headers.update(extra)
    return headers


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


async def _proxy_post(path: str, request: Request) -> Response:
    """Forward a POST request to the Payments service."""
    settings = gateway_settings()
    url = f"{settings.payments_base_url}{path}"
    body = await request.body()
    headers = _forward_headers(request)
    timeout = httpx.Timeout(
        10.0, 
        read=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream = await client.post(url, content=body, headers=headers)
    content_type = upstream.headers.get("content-type")
    response_headers = _select_response_headers(upstream.headers)
    
    return Response(
        content=upstream.content, 
        status_code=upstream.status_code, 
        media_type=content_type, 
        headers=response_headers
        )


async def _proxy_get(path: str, request: Request) -> Response:
    """Forward a GET request to the Payments service."""
    settings = gateway_settings()
    url = f"{settings.payments_base_url}{path}"
    headers = _forward_headers(request)
    timeout = httpx.Timeout(10.0, read=20.0)
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream = await client.get(url, headers=headers, params=params)
    content_type = upstream.headers.get("content-type")
    response_headers = _select_response_headers(upstream.headers)
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=content_type, headers=response_headers)


@router.post("/intents")
async def create_intent(request: Request) -> Response:
    """Create a payment intent (proxy)."""
    return await _proxy_post("/payments/intents", request)


@router.post("/intents/{intent_id}/confirm")
async def confirm_intent(intent_id: str, request: Request) -> Response:
    """Confirm a payment intent, triggering downstream evaluation (proxy)."""
    return await _proxy_post(f"/payments/intents/{intent_id}/confirm", request)


@router.get("/intents/{intent_id}")
async def get_intent(intent_id: str, request: Request) -> Response:
    """Fetch a payment intent by id (proxy)."""
    return await _proxy_get(f"/payments/intents/{intent_id}", request)
