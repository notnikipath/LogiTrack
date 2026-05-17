from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "logitrack-service"
    service_port: int = 8400
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://logitrack:logitrack@postgres:5432/logitrack"
    redis_url: str = "redis://redis:6379/0"
    timescale_dsn: str = "postgresql+psycopg://logitrack:logitrack@timescaledb:5432/logitrack"
    kafka_bootstrap_servers: str = "redpanda:9092"
    maps_provider_url: str = "https://tile.openstreetmap.org"

    jwt_secret: str = "logitrack-dev-secret"
    encryption_key: str = "logitrack-dev-encryption-key"

    route_build_target_seconds: float = 5.0
    eta_mape_target: float = 10.0
    concurrent_vehicle_target: int = 5000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()