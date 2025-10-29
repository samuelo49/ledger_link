from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", env_file_encoding="utf-8")

    port: int = 8080
    jwt_audience: str = "fintech-partners"
    jwt_issuer: str = "http://identity-service:8000"
    secret_key: str = "changeme"
    requests_per_minute: int = 120
    rate_limit_window_seconds: int = 60


@lru_cache
def gateway_settings() -> GatewaySettings:
    return GatewaySettings()
