from __future__ import annotations

"""Wallet proxy routes for the API Gateway.

Exposes wallet endpoints under ``/api/v1/wallets`` and forwards to the Wallet
service. This layer is deliberately thin and focused on forwarding requests
with safe headers; balance and ledger logic live in the Wallet service.
"""

from typing import Iterable

import httpx
from fastapi import APIRouter, Request, Response

from ..settings import gateway_settings

router = APIRouter(prefix="/api/v1/wallets")


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
    """Forward a POST request to the Wallet service."""
    settings = gateway_settings()
    url = f"{settings.wallet_base_url}{path}"
    body = await request.body()
    headers = _forward_headers(request)
    timeout = httpx.Timeout(10.0, read=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream = await client.post(url, content=body, headers=headers)
    content_type = upstream.headers.get("content-type")
    response_headers = _select_response_headers(upstream.headers)
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=content_type, headers=response_headers)


async def _proxy_get(path: str, request: Request) -> Response:
    """Forward a GET request to the Wallet service."""
    settings = gateway_settings()
    url = f"{settings.wallet_base_url}{path}"
    headers = _forward_headers(request)
    timeout = httpx.Timeout(10.0, read=20.0)
    params = dict(request.query_params)
    async with httpx.AsyncClient(timeout=timeout) as client:
        upstream = await client.get(url, headers=headers, params=params)
    content_type = upstream.headers.get("content-type")
    response_headers = _select_response_headers(upstream.headers)
    return Response(content=upstream.content, status_code=upstream.status_code, media_type=content_type, headers=response_headers)


@router.post("")
async def create_wallet(request: Request) -> Response:
    """Create a wallet for the current user (proxy)."""
    return await _proxy_post("/wallets", request)


@router.post("/{wallet_id}/credit")
async def credit_wallet(wallet_id: str, request: Request) -> Response:
    """Credit funds to a wallet (proxy)."""
    return await _proxy_post(f"/wallets/{wallet_id}/credit", request)


@router.post("/{wallet_id}/debit")
async def debit_wallet(wallet_id: str, request: Request) -> Response:
    """Debit funds from a wallet (proxy)."""
    return await _proxy_post(f"/wallets/{wallet_id}/debit", request)


@router.get("/{wallet_id}/balance")
async def wallet_balance(wallet_id: str, request: Request) -> Response:
    """Return the current balance for a wallet (proxy)."""
    return await _proxy_get(f"/wallets/{wallet_id}/balance", request)
