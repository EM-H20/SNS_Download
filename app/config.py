"""Application configuration management using Pydantic Settings.

Centralizes all configuration with type validation and environment variable support.
"""

import json
import random
from pathlib import Path
from typing import Literal, Optional, List, Dict

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with validation and type safety."""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env

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
    request_timeout_seconds: int = 30
    max_retries: int = 3

    # User Agent Pool (다양한 브라우저/OS 조합으로 차단 우회)
    _user_agent_pool: list[str] = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    def get_random_user_agent(self) -> str:
        """다양한 USER_AGENT 중 랜덤하게 선택 (차단 우회용)"""
        return random.choice(self._user_agent_pool)

    # Instagram Authentication (Multiple Accounts for Rotation)
    # 단일 계정 (하위 호환성)
    instagram_username: Optional[str] = None
    instagram_password: Optional[str] = None

    # 다중 계정 (JSON 배열 형식)
    # 예: [{"username":"user1","password":"pass1"},{"username":"user2","password":"pass2"}]
    instagram_accounts_json: Optional[str] = None

    # Instagram Graph API (Official API for business accounts)
    instagram_graph_api_token: Optional[str] = None
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None

    # Metadata Collection
    save_metadata: bool = True  # Save captions, hashtags, etc. to JSON
    include_comments: bool = False  # Fetch comments (requires Instagram auth)
    max_comments: int = 50  # Maximum comments to fetch per post

    def get_instagram_accounts(self) -> List[Dict[str, str]]:
        """Instagram 계정 리스트 반환 (단일 또는 다중).

        우선순위:
        1. instagram_accounts_json (다중 계정)
        2. instagram_username/password (단일 계정, 하위 호환성)

        Returns:
            [{"username": "user1", "password": "pass1"}, ...]
        """
        accounts = []

        # 1순위: 다중 계정 JSON
        if self.instagram_accounts_json:
            try:
                accounts = json.loads(self.instagram_accounts_json)
                if not isinstance(accounts, list):
                    raise ValueError("INSTAGRAM_ACCOUNTS_JSON must be a JSON array")
                return accounts
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid INSTAGRAM_ACCOUNTS_JSON format: {e}")

        # 2순위: 단일 계정 (하위 호환성)
        if self.instagram_username and self.instagram_password:
            accounts = [
                {"username": self.instagram_username, "password": self.instagram_password}
            ]

        return accounts

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure download directory exists on initialization
        self.download_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance - initialized once at startup
settings = Settings()

# Instagram 계정 관리자 초기화 (다중 계정 지원)
from app.account_manager import InstagramAccountManager

instagram_accounts = settings.get_instagram_accounts()
if instagram_accounts:
    account_manager = InstagramAccountManager(instagram_accounts)
else:
    account_manager = None
