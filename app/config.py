from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_primary_model: str = "z-ai/glm-5.2:free"
    openrouter_fallback_models: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["openrouter/free", "qwen/qwen3.7-flash"]
    )
    openrouter_site_url: str = ""
    openrouter_app_name: str = "Maaz Sample Lead Validator"
    openrouter_timeout_seconds: float = 45.0
    openrouter_retries_per_model: int = 1
    database_path: str = "data/leads.db"
    crawl_max_pages: int = Field(default=10, ge=1, le=10)
    crawl_timeout_seconds: float = 12.0
    crawl_user_agent: str = "MaazLeadValidator/0.1"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    sales_notification_email: str = ""
    log_level: str = "INFO"
    log_file: str = "logs/app.log"

    @field_validator("openrouter_fallback_models", mode="before")
    @classmethod
    def parse_fallback_models(cls, value: object) -> object:
        if isinstance(value, str):
            return [model.strip() for model in value.split(",") if model.strip()]
        return value

    @property
    def openrouter_models(self) -> list[str]:
        return list(dict.fromkeys(
            [self.openrouter_primary_model, *self.openrouter_fallback_models]
        ))


@lru_cache
def get_settings() -> Settings:
    return Settings()
