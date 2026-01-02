from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from loguru import logger
from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class IdentitySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IDENTITY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # safer for Docker/K8s
    )

    # --- Core metadata ---
    service_name: str = "identity-service"
    environment: str = "local"
    log_level: str = "INFO"

    # --- Database + cache ---
    database_url: AnyUrl = "postgresql+asyncpg://identity_user:identity_password@identity-db:5432/identity_db"
    database_sync_url: AnyUrl = "postgresql+psycopg://identity_user:identity_password@identity-db:5432/identity_db"
    redis_url: AnyUrl = "redis://redis:6379/0"

    # --- JWT / Security ---
    jwt_issuer: str = "http://identity-service:8000"
    jwt_audience: str = "fintech-platform"
    access_token_expires_minutes: int = 15
    refresh_token_expires_minutes: int = 1440
    jwt_key_id: str = "ledgerlink-dev"
    jwt_private_key: str | None = None
    jwt_public_key: str | None = None
    jwt_private_key_path: str | None = None
    jwt_public_key_path: str | None = None
    jwt_keys_dir: str = "services/identity_service/app/keys"
    # Login policy
    max_failed_login_attempts: int = 5
    lockout_minutes: int = 15
    require_verified_for_login: bool = False

    # --- Observability ---
    otel_endpoint: AnyUrl = "http://jaeger:4317"

    # --- Default admin seeding (dev only) ---
    default_admin_email: str = "admin@ledgerlink.io"
    default_admin_password: str = "Admin123!"
    default_admin_is_superuser: bool = True

    @property
    def async_db_url(self) -> str:
        """Return string form of async database URL for SQLAlchemy."""
        return str(self.database_url)

    @property
    def sync_db_url(self) -> str:
        """Return string form of sync database URL for Alembic or testing."""
        return str(self.database_sync_url)

    @property
    def private_key_path(self) -> Path:
        if self.jwt_private_key_path:
            return Path(self.jwt_private_key_path)
        return Path(self.jwt_keys_dir) / "jwt_private.pem"

    @property
    def public_key_path(self) -> Path:
        if self.jwt_public_key_path:
            return Path(self.jwt_public_key_path)
        return Path(self.jwt_keys_dir) / "jwt_public.pem"

    def safe_dict(self) -> dict[str, str]:
        """Return non-sensitive settings for debug logs."""
        return {
            "environment": self.environment,
            "service_name": self.service_name,
            "database_host": self.database_url.host,
            "redis_host": self.redis_url.host,
            "jwt_issuer": self.jwt_issuer,
            "jwt_key_id": self.jwt_key_id,
            "otel_endpoint": self.otel_endpoint,
        }


@lru_cache
def identity_settings() -> IdentitySettings:
    settings = IdentitySettings()

    # --- Configure Loguru log level ---
    logger.remove()  # clear default sink
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=settings.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
    )

    # --- Print safe startup configuration summary ---
    safe_info = settings.safe_dict()
    logger.info("🚀 [Startup] Service configuration summary:")
    for key, value in safe_info.items():
        logger.info(f"    {key}: {value}")

    logger.info("✅ Configuration loaded successfully.\n")

    return settings
