from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "ThreatLens"
    app_version: str = "1.4.0"
    app_env: Literal["development", "test", "production"] = "development"
    app_secret_key: str = "development-only-change-me"
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:4200"
    database_url: str = "postgresql+asyncpg://threatlens:threatlens@localhost:5432/threatlens"
    redis_url: str | None = None
    access_token_minutes: int = Field(default=30, ge=5, le=1440)
    auto_create_schema: bool = False
    seed_source_catalog: bool = True
    seed_default_playbooks: bool = True
    monitoring_scheduler_enabled: bool = True
    monitoring_poll_seconds: int = Field(default=60, ge=10, le=3600)
    log_level: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        return [self.frontend_url]

    @model_validator(mode="after")
    def reject_default_production_secret(self) -> "Settings":
        if self.app_env == "production" and self.app_secret_key == "development-only-change-me":
            raise ValueError("APP_SECRET_KEY must be configured in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
