"""Typed, environment-based application settings.

All configuration comes from environment variables (or an optional .env
file). Nothing sensitive is hard-coded in source code.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env files."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    app_name: str = "RoleShift AI"
    app_version: str = "0.1.0"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_debug: bool = False
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # API
    api_v1_prefix: str = "/api/v1"

    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_database: str = "roleshift"
    mongodb_timeout_ms: int = Field(default=5000, ge=1000, le=60000)

    # AI provider
    ai_provider: str = Field(
        default="deepseek",
        description="Provider name: 'deepseek', 'ollama_cloud', or 'none' to disable",
    )
    ai_model: str = Field(default="deepseek-chat", max_length=200)
    ai_api_key: str = Field(default="", max_length=500)
    ai_api_base_url: str = Field(default="https://api.deepseek.com", max_length=500)
    ollama_api_key: str = Field(default="", max_length=500)
    ai_timeout_seconds: int = Field(default=60, ge=10, le=300)
    ai_max_retries: int = Field(default=0, ge=0, le=3)
    ai_temperature: float = Field(default=0.3, ge=0.0, le=2.0)

    # CORS - comma-separated list of allowed origins.
    # Production deployments must configure explicit origins (no wildcard).
    # NoDecode: env values arrive as raw strings and are split by the
    # validator below (avoids pydantic-settings JSON-parsing list fields).
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            return origins
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (re-read .env only on restart)."""
    return Settings()