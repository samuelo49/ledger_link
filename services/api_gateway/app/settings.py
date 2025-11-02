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
    # Upstream identity service base URL (inside the Docker network by default)
    identity_base_url: str = "http://identity-service:8000/api/v1"
    # Upstream wallet service base URL
    wallet_base_url: str = "http://wallet-service:8000/api/v1"
    # Upstream payments service base URL
    payments_base_url: str = "http://payments-service:8000/api/v1"


@lru_cache
def gateway_settings() -> GatewaySettings:
    return GatewaySettings()
