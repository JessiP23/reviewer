from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./reviewer.db"
    cors_origins: str = "http://localhost:3000"
    max_upload_bytes: int = 10 * 1024 * 1024
    repository_backend: Literal["sqlalchemy", "rds-data"] = "sqlalchemy"
    job_backend: Literal["in-process", "sqs"] = "in-process"
    aws_region: str = "us-east-2"
    document_bucket: str | None = None
    document_store_path: str = "./document_store"
    review_queue_url: str | None = None
    rds_cluster_arn: str | None = None
    rds_secret_arn: str | None = None
    rds_database: str = "reviewer"
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
