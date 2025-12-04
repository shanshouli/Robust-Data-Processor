"""Application configuration and settings."""

from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Environment-driven application settings."""

    aws_region: str = Field(..., env="AWS_REGION")
    sqs_queue_url: str = Field(..., env="SQS_QUEUE_URL")
    dynamodb_table_name: str = Field(..., env="DYNAMODB_TABLE_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()

