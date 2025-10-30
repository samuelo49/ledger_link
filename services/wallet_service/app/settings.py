from functools import lru_cache
from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class WalletSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WALLET_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "wallet-service"
    environment: str = "local"
    log_level: str = "INFO"

    database_url: AnyUrl = "postgresql+asyncpg://wallet_user:wallet_password@wallet-db:5432/wallet_db"
    database_sync_url: AnyUrl = "postgresql+psycopg://wallet_user:wallet_password@wallet-db:5432/wallet_db"
    redis_url: AnyUrl = "redis://redis:6379/1"

    @property
    def async_db_url(self) -> str:
        return str(self.database_url)

    @property
    def sync_db_url(self) -> str:
        return str(self.database_sync_url)


@lru_cache
def wallet_settings() -> WalletSettings:
    return WalletSettings()
