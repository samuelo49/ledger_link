"""Service catalog and aggregated OpenAPI endpoints.

Provides:
* GET /api/v1/catalog            -> Summary of each upstream service (paths only)
* GET /api/v1/openapi-aggregate  -> Synthetic merged OpenAPI (paths only, prefixed)

Notes:
* Prefixes each service's paths under /{service}/{rest-of-original-path-without-leading-/api/v1}
  to avoid collisions (e.g. identity /api/v1/auth/register => /identity/auth/register).
* Components/schemas are intentionally omitted for simplicity; extend later if needed.
* Unreachable services are skipped with an error entry in the catalog list.
"""

from __future__ import annotations

from typing import Any, Dict

import httpx
from fastapi import APIRouter, Response

from ..settings import gateway_settings

router = APIRouter()


SERVICE_MAP = {
    "identity": "identity_base_url",
    "wallet": "wallet_base_url",
    "payments": "payments_base_url",
    "risk": "risk_base_url",
}


def _service_root(base_url: str) -> str:
    # identity_base_url is like http://identity-service:8000/api/v1
    if base_url.endswith("/api/v1"):
        return base_url[:-len("/api/v1")]
    return base_url.rstrip("/")


async def _fetch_openapi(client: httpx.AsyncClient, root: str) -> Dict[str, Any]:
    resp = await client.get(f"{root}/openapi.json", timeout=httpx.Timeout(5.0))
    resp.raise_for_status()
    return resp.json()


def _strip_api_v1(path: str) -> str:
    return path[len("/api/v1"):] if path.startswith("/api/v1") else path


@router.get("/api/v1/catalog", tags=["catalog"])
async def catalog() -> Dict[str, Any]:
    settings = gateway_settings()
    out: Dict[str, Any] = {"services": []}
    async with httpx.AsyncClient() as client:
        for slug, attr in SERVICE_MAP.items():
            base = getattr(settings, attr)
            root = _service_root(base)
            try:
                spec = await _fetch_openapi(client, root)
                paths = list(spec.get("paths", {}).keys())
                out["services"].append({
                    "name": slug,
                    "root": root,
                    "original_path_count": len(paths),
                    "paths": paths,
                })
            except Exception as e:  # noqa: BLE001
                out["services"].append({
                    "name": slug,
                    "root": root,
                    "error": str(e),
                })
    return out


@router.get("/api/v1/openapi-aggregate", tags=["catalog"])
async def openapi_aggregate() -> Dict[str, Any]:
    settings = gateway_settings()
    aggregate: Dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {"title": "Fintech Aggregate API", "version": "0.1.0"},
        "paths": {},
        "servers": [],
    }
    async with httpx.AsyncClient() as client:
        for slug, attr in SERVICE_MAP.items():
            base = getattr(settings, attr)
            root = _service_root(base)
            try:
                spec = await _fetch_openapi(client, root)
                aggregate["servers"].append({"url": root, "description": f"Upstream {slug}"})
                for p, val in spec.get("paths", {}).items():
                    new_path = f"/{slug}{_strip_api_v1(p)}"
                    # Shallow copy; deep merge of methods if collision
                    if new_path in aggregate["paths"]:
                        # Merge operations without overwriting existing methods
                        existing = aggregate["paths"][new_path]
                        for method, op in val.items():
                            if method not in existing:
                                existing[method] = op
                    else:
                        aggregate["paths"][new_path] = val
            except Exception:
                # Skip unreachable service in aggregate spec.
                continue
    return aggregate
