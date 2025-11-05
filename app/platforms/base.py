"""Base platform interface for SNS downloaders.

All platform-specific downloaders must inherit from BasePlatform
and implement the required methods.
"""

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from app.models import MediaMetadata


class PlatformType(str, Enum):
    """Supported social media platforms."""
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    FACEBOOK = "facebook"


class BasePlatform(ABC):
    """Abstract base class for platform-specific downloaders."""

    @property
    @abstractmethod
    def platform_name(self) -> PlatformType:
        """Platform identifier."""
        pass

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Check if this platform can handle the given URL.

        Args:
            url: Social media URL

        Returns:
            True if this platform can download from this URL
        """
        pass

    @abstractmethod
    def extract_identifier(self, url: str) -> str:
        """Extract platform-specific identifier from URL.

        Args:
            url: Social media URL

        Returns:
            Platform-specific identifier (e.g., shortcode, video_id)

        Raises:
            ValueError: If URL format is invalid
        """
        pass

    @abstractmethod
    def download(
        self,
        url: str,
        output_dir: Optional[Path] = None
    ) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download media from the given URL.

        Args:
            url: Social media URL
            output_dir: Optional output directory

        Returns:
            Tuple of (media_path, thumbnail_path, metadata)

        Raises:
            ContentNotFoundError: Content doesn't exist or was deleted
            DownloadFailedError: Download failed
            Various platform-specific exceptions
        """
        pass

    def get_platform_info(self) -> dict:
        """Get platform information and capabilities.

        Returns:
            Dictionary with platform metadata
        """
        return {
            "platform": self.platform_name.value,
            "supported_types": ["video", "image"],
            "requires_auth": False,
        }
