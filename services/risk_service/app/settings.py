from functools import lru_cache
from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class RiskSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RISK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "risk-service"
    environment: str = "local"
    log_level: str = "INFO"

    database_url: AnyUrl = "postgresql+asyncpg://risk_user:risk_password@risk-db:5432/risk_db"
    database_sync_url: AnyUrl = "postgresql+psycopg://risk_user:risk_password@risk-db:5432/risk_db"
    redis_url: AnyUrl = "redis://redis:6379/3"

    @property
    def async_db_url(self) -> str:
        return str(self.database_url)

    @property
    def sync_db_url(self) -> str:
        return str(self.database_sync_url)


@lru_cache
def risk_settings() -> RiskSettings:
    return RiskSettings()
