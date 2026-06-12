from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Transaction Pipeline"
    environment: Literal["local", "test", "staging", "production"] = "local"
    log_level: str = "INFO"

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@postgres:5432/transactions",
        validation_alias="DATABASE_URL",
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@postgres:5432/transactions",
        validation_alias="SYNC_DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", validation_alias="REDIS_URL")

    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = "gemini-1.5-flash"
    llm_timeout_seconds: float = 20.0
    llm_max_retries: int = 4

    upload_max_bytes: int = 100 * 1024 * 1024
    upload_dir: str = "/tmp/transaction-uploads"
    storage_provider: Literal["local", "s3"] = "local"
    s3_bucket_name: str = "ai-transaction-uploads"
    csv_batch_size: int = 5_000

    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
