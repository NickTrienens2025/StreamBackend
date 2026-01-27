"""
Configuration management for GetStream backend
Loads settings from environment variables
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App settings
    APP_NAME: str = "GetStream Activity Feeds API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # GetStream configuration
    STREAM_API_KEY: str
    STREAM_API_SECRET: str
    STREAM_APP_ID: Optional[str] = None

    # Feed configuration
    DEFAULT_FEED_GROUP: str = "goals"
    CENTRAL_FEED_ID: str = "nhl"

    # API settings
    API_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: str = "*"  # Comma-separated list of allowed origins

    # Pagination
    DEFAULT_LIMIT: int = 50
    MAX_LIMIT: int = 1000

    # S3-Compatible Storage
    S3_BASE_URL: str = "https://s3.foreverflow.click/api/hockeyGoals"
    S3_ENABLED: bool = True

    # Startup Scraper
    STARTUP_SCRAPER_ENABLED: bool = True
    STARTUP_SCRAPER_DAYS_BACK: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True


# Singleton settings instance
settings = Settings()
