from __future__ import annotations

from functools import lru_cache
from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    supabase_url: AnyHttpUrl
    supabase_publishable_key: SecretStr
    database_url: SecretStr
    app_secret_key: SecretStr
    frontend_url: AnyHttpUrl = AnyHttpUrl("http://localhost:5173")
    backend_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8000")
    cors_origins: list[AnyHttpUrl] = Field(default_factory=lambda: [AnyHttpUrl("http://localhost:5173")])
    cookie_secure: bool = True
    oauth_cookie_name: str = "systemlab_oauth_flow"
    refresh_cookie_name: str = "systemlab_refresh_token"
    oauth_cookie_max_age: int = 600
    refresh_cookie_max_age: int = 60 * 60 * 24 * 30
    queue_name: str = "analysis_jobs"
    queue_visibility_seconds: int = 900
    queue_poll_seconds: int = 5
    queue_max_attempts: int = 3
    database_pool_min_size: int = 1
    database_pool_max_size: int = 5

    @field_validator("cors_origins")
    @classmethod
    def cors_must_be_explicit(cls, value: list[AnyHttpUrl]) -> list[AnyHttpUrl]:
        if not value:
            raise ValueError("At least one CORS origin is required")
        if any(str(origin) == "*" for origin in value):
            raise ValueError("Wildcard CORS origins are not allowed")
        return value

    @field_validator("app_secret_key")
    @classmethod
    def app_secret_must_be_strong(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("APP_SECRET_KEY must contain at least 32 characters")
        return value

    @property
    def oauth_callback_url(self) -> str:
        return f"{str(self.backend_url).rstrip('/')}/api/v1/auth/callback"

    @property
    def frontend_callback_url(self) -> str:
        return f"{str(self.frontend_url).rstrip('/')}/auth/callback"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

