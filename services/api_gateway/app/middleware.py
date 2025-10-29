from __future__ import annotations

import time
import uuid
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from loguru import logger

from .settings import gateway_settings


class SlidingWindowLimiter:
    """Simple in-memory rate limiter for local development."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def allow(self, identifier: str) -> bool:
        now = time.time()
        window_start = now - self.window
        bucket = self._buckets[identifier]
        while bucket and bucket[0] < window_start:
            bucket.pop(0)
        if len(bucket) >= self.limit:
            return False
        bucket.append(now)
        return True


def request_id_middleware() -> Callable:
    async def middleware(request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        elapsed = (time.time() - start) * 1000
        response.headers["x-request-id"] = request_id
        logger.bind(request_id=request_id).info(
            "Gateway %s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response

    return middleware


def rate_limit_middleware(limiter: SlidingWindowLimiter) -> Callable:
    async def middleware(request: Request, call_next: Callable) -> Response:
        client_id = request.headers.get("x-api-key") or request.client.host or "anonymous"
        if not limiter.allow(client_id):
            return Response(status_code=429, content="Too Many Requests")
        return await call_next(request)

    return middleware


def setup_middleware(app: FastAPI) -> None:
    settings = gateway_settings()
    limiter = SlidingWindowLimiter(
        settings.requests_per_minute, window_seconds=settings.rate_limit_window_seconds
    )
    app.middleware("http")(request_id_middleware())
    app.middleware("http")(rate_limit_middleware(limiter))
