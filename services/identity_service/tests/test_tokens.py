from __future__ import annotations

import os
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.identity_service.app.db.base import Base
from services.identity_service.app.dependencies import get_session
from services.identity_service.app.main import create_app
from services.identity_service.app.settings import identity_settings


def _generate_key_pair() -> tuple[str, str]:
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
    return private_pem.decode("utf-8"), public_pem.decode("utf-8")


@pytest.fixture
async def test_app(monkeypatch):
    private_key, public_key = _generate_key_pair()
    monkeypatch.setenv("IDENTITY_JWT_PRIVATE_KEY", private_key)
    monkeypatch.setenv("IDENTITY_JWT_PUBLIC_KEY", public_key)
    identity_settings.cache_clear()

    app = create_app()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_session() -> AsyncSession:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield app

    await engine.dispose()
    identity_settings.cache_clear()
    monkeypatch.delenv("IDENTITY_JWT_PRIVATE_KEY", raising=False)
    monkeypatch.delenv("IDENTITY_JWT_PUBLIC_KEY", raising=False)


async def _register_and_login(client: AsyncClient, email: str, password: str) -> dict:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = await client.post("/api/v1/auth/token", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


@pytest.mark.asyncio
async def test_refresh_rotation_invalidates_previous_token(test_app):
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        email = f"user-{uuid4()}@example.com"
        tokens = await _register_and_login(client, email, "Passw0rd!")

        first_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert first_refresh.status_code == 200

        replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert replay.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(test_app):
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        email = f"user-{uuid4()}@example.com"
        tokens = await _register_and_login(client, email, "Passw0rd!")

        logout = await client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
        assert logout.status_code == 204

        replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert replay.status_code == 401


@pytest.mark.asyncio
async def test_jwks_endpoint_exposes_public_key(test_app):
    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        response = await client.get("/api/v1/auth/jwks")
        assert response.status_code == 200
        payload = response.json()
        assert "keys" in payload
        assert payload["keys"][0]["kty"] == "RSA"
        assert payload["keys"][0]["alg"] == "RS256"
