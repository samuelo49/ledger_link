from functools import lru_cache

from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IDENTITY_", env_file=".env", env_file_encoding="utf-8")

    service_name: str = "identity-service"
    database_url: AnyUrl = "postgresql+asyncpg://identity_user:identity_password@identity-db:5432/identity_db"
    database_sync_url: AnyUrl = "postgresql://identity_user:identity_password@identity-db:5432/identity_db"
    redis_url: AnyUrl = "redis://redis:6379/0"
    jwt_issuer: str = "http://identity-service:8000"
    jwt_audience: str = "fintech-platform"
    secret_key: str = "change-me"
    access_token_expires_minutes: int = 15
    refresh_token_expires_minutes: int = 1440
    otel_endpoint: str = "http://jaeger:4317"


@lru_cache
def identity_settings() -> IdentitySettings:
    return IdentitySettings()
