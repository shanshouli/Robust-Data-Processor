"""Application configuration and settings.

This module provides environment-driven configuration management using Pydantic.
All settings are loaded from environment variables or an optional .env file.
"""

from functools import lru_cache
from pydantic import BaseSettings, Field


class IngestSettings(BaseSettings):
    """Settings for the ingestion Lambda (FastAPI)."""

    aws_region: str = Field(..., env="AWS_REGION")  # Lambda provides this automatically
    sqs_queue_url: str = Field(..., env="SQS_QUEUE_URL")
    dynamodb_table_name: str = Field(..., env="DYNAMODB_TABLE_NAME")

    class Config:
        env_file = ".env"  # Optional .env file path for local development
        env_file_encoding = "utf-8"


class WorkerSettings(BaseSettings):
    """Settings for the worker Lambda (SQS consumer)."""

    aws_region: str = Field(..., env="AWS_REGION")
    dynamodb_table_name: str = Field(..., env="DYNAMODB_TABLE_NAME")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Backwards compatibility alias for code/tests already importing Settings.
Settings = IngestSettings


@lru_cache()
def get_settings() -> IngestSettings:
    """Return cached ingestion settings instance."""
    return IngestSettings()


@lru_cache()
def get_worker_settings() -> WorkerSettings:
    """Return cached worker settings instance."""
    return WorkerSettings()
