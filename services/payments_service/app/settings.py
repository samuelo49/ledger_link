from functools import lru_cache
from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class PaymentsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PAYMENTS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "payments-service"
    environment: str = "local"
    log_level: str = "INFO"

    database_url: AnyUrl = "postgresql+asyncpg://payments_user:payments_password@payments-db:5432/payments_db"
    database_sync_url: AnyUrl = "postgresql+psycopg://payments_user:payments_password@payments-db:5432/payments_db"
    redis_url: AnyUrl = "redis://redis:6379/2"
    jwt_audience: str = "fintech-partners"
    jwt_issuer: str = "http://identity-service:8000"
    secret_key: str = "changeme"

    @property
    def async_db_url(self) -> str:
        return str(self.database_url)

    @property
    def sync_db_url(self) -> str:
        return str(self.database_sync_url)


@lru_cache
def payments_settings() -> PaymentsSettings:
    return PaymentsSettings()
