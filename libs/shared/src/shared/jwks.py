from __future__ import annotations

import json
import threading
import time
from typing import Dict

import httpx
from jose import jwt
from jose.exceptions import JWTError


class JWKSClient:
    """Fetch and cache JSON Web Key Sets for RSA signature verification."""

    def __init__(self, jwks_url: str, cache_ttl: int = 300) -> None:
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._lock = threading.Lock()
        self._keys: Dict[str, str] = {}
        self._expires_at: float = 0.0

    def get_key(self, kid: str) -> str:
        """Return a PEM-encoded public key for the provided key id."""
        with self._lock:
            if time.time() >= self._expires_at or kid not in self._keys:
                self._refresh_keys()
            key = self._keys.get(kid)
        if not key:
            raise KeyError(f"Signing key with kid={kid} not found in JWKS")
        return key

    def _refresh_keys(self) -> None:
        response = httpx.get(self.jwks_url, timeout=5.0)
        response.raise_for_status()
        data = response.json()
        keys: Dict[str, str] = {}
        for jwk in data.get("keys", []):
            kid = jwk.get("kid")
            if not kid:
                continue
            pem = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
            keys[kid] = pem
        if not keys:
            raise ValueError("JWKS endpoint returned no signing keys")
        self._keys = keys
        self._expires_at = time.time() + self.cache_ttl
