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

    @property
    def live_enabled(self) -> bool:
        return self.app_mode == "live" and bool(self.openai_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
