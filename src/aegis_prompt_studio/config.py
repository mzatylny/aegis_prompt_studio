from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.6", alias="OPENAI_MODEL")
    openai_research_model: str = Field(default="gpt-5.6", alias="OPENAI_RESEARCH_MODEL")
    app_mode: Literal["demo", "live"] = Field(default="demo", alias="APP_MODE")
    max_research_sources: int = Field(default=12, ge=3, le=50, alias="MAX_RESEARCH_SOURCES")
    max_input_chars: int = Field(default=50_000, ge=1_000, le=500_000, alias="MAX_INPUT_CHARS")
    max_concurrent_research: int = Field(
        default=2,
        ge=1,
        le=32,
        alias="MAX_CONCURRENT_RESEARCH",
    )
    api_access_key: str | None = Field(default=None, alias="AEGIS_API_KEY")
    api_url: str = Field(default="http://127.0.0.1:8000", alias="AEGIS_API_URL")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        alias="AEGIS_LOG_LEVEL",
    )
    cors_origins: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501",
        alias="CORS_ORIGINS",
    )

    @property
    def live_enabled(self) -> bool:
        return self.app_mode == "live" and bool(self.openai_api_key)

    @property
    def configuration_ready(self) -> bool:
        """Report whether the selected runtime mode has its required configuration."""
        return self.app_mode == "demo" or bool(self.openai_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
