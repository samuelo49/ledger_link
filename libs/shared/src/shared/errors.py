from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from .request_context import REQUEST_ID_HEADER
from .schemas import ErrorResponse


def _serialize_detail(detail: str | dict | None) -> str | None:
    if detail is None:
        return None
    if isinstance(detail, (str, int, float)):
        return str(detail)
    return str(detail)


def error_response(status_code: int, error: str, detail: str | dict | None, request_id: str | None) -> JSONResponse:
    payload = ErrorResponse(error=error, detail=_serialize_detail(detail), request_id=request_id)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return error_response(exc.status_code, error=str(exc.detail) if exc.detail else exc.__class__.__name__, detail=exc.detail, request_id=request_id)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return error_response(500, error="Internal Server Error", detail=str(exc), request_id=request_id)
