from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..settings import identity_settings


def _generate_rsa_keypair(private_path: Path, public_path: Path) -> tuple[str, str]:
    private_path.parent.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    return private_pem.decode("utf-8"), public_pem.decode("utf-8")


def _load_or_generate_keys() -> tuple[str, str]:
    settings = identity_settings()

    if settings.jwt_private_key and settings.jwt_public_key:
        return settings.jwt_private_key, settings.jwt_public_key

    private_path = settings.private_key_path
    public_path = settings.public_key_path

    if private_path.exists() and public_path.exists():
        return private_path.read_text(), public_path.read_text()

    return _generate_rsa_keypair(private_path, public_path)


@lru_cache
def get_private_key() -> str:
    private_key, _ = _load_or_generate_keys()
    return private_key


@lru_cache
def get_public_key() -> str:
    _, public_key = _load_or_generate_keys()
    return public_key


def build_jwk() -> dict[str, Any]:
    """Return the RSA public key represented as a JWKS entry."""
    settings = identity_settings()
    public_key = serialization.load_pem_public_key(get_public_key().encode("utf-8"))
    numbers = public_key.public_numbers()
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, byteorder="big")
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, byteorder="big")
    return {
        "kty": "RSA",
        "kid": settings.jwt_key_id,
        "use": "sig",
        "alg": "RS256",
        "n": base64.urlsafe_b64encode(n).rstrip(b"=").decode("utf-8"),
        "e": base64.urlsafe_b64encode(e).rstrip(b"=").decode("utf-8"),
    }
