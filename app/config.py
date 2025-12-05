"""Application configuration and settings.

This module provides environment-driven configuration management using Pydantic.
All settings are loaded from environment variables or an optional .env file.
"""

from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Environment-driven application settings.
    
    This class defines all required configuration parameters for the application.
    Values are loaded from environment variables, with optional .env file support.
    
    Attributes:
        aws_region: AWS region for all services (SQS, DynamoDB, etc.)
                    Lambda automatically provides this via AWS_REGION env var
        sqs_queue_url: Full URL of the SQS queue for log message ingestion
        dynamodb_table_name: Name of the DynamoDB table for storing processed logs
    """

    aws_region: str = Field(..., env="AWS_REGION")  # Lambda provides this automatically
    sqs_queue_url: str = Field(..., env="SQS_QUEUE_URL")
    dynamodb_table_name: str = Field(..., env="DYNAMODB_TABLE_NAME")

    class Config:
        """Pydantic configuration for Settings."""
        env_file = ".env"  # Optional .env file path for local development
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance.
    
    Uses LRU cache to ensure settings are loaded only once per application lifecycle,
    improving performance and ensuring consistency.
    
    Returns:
        Settings: A singleton instance of application settings
    """
    return Settings()

