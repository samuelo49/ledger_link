from __future__ import annotations

from typing import Callable
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

REQUEST_ID_HEADER = "x-request-id"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Ensure every request has an `x-request-id` header for traceability."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        if REQUEST_ID_HEADER not in response.headers:
            response.headers[REQUEST_ID_HEADER] = request_id
        return response
