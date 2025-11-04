"""Application configuration management using Pydantic Settings.

Centralizes all configuration with type validation and environment variable support.
"""

from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings with validation and type safety."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Server Configuration
    server_host: str = "127.0.0.1"
    server_port: int = 8000
    environment: Literal["development", "production"] = "development"

    # Storage Configuration
    download_dir: Path = Path("./downloads")
    max_file_size_mb: int = 100

    # Rate Limiting
    rate_limit_per_minute: int = 10

    # Instagram Scraping
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    request_timeout_seconds: int = 30
    max_retries: int = 3

    # Instagram Authentication (Optional - for carousel/private content support)
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure download directory exists on initialization
        self.download_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance - initialized once at startup
settings = Settings()
