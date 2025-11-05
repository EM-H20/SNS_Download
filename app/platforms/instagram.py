"""Instagram platform downloader.

Wraps existing Instagram downloader functionality into the platform interface.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from app.config import settings
from app.models import MediaMetadata
from app.downloader import ReelsDownloader
from app.parser import ReelsURLParser
from .base import BasePlatform, PlatformType

logger = logging.getLogger(__name__)


class InstagramPlatform(BasePlatform):
    """Instagram downloader platform wrapper."""

    def __init__(self):
        """Initialize Instagram platform."""
        self.parser = ReelsURLParser()
        self.downloader = ReelsDownloader()

    @property
    def platform_name(self) -> PlatformType:
        return PlatformType.INSTAGRAM

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Instagram."""
        # Simple domain check first
        if "instagram.com" not in url:
            return False

        # Then try to extract shortcode
        try:
            self.parser.extract_shortcode(url)
            return True
        except (ValueError, Exception):
            return False

    def extract_identifier(self, url: str) -> str:
        """Extract shortcode from Instagram URL.

        Args:
            url: Instagram URL

        Returns:
            Shortcode (8-15 characters)

        Raises:
            ValueError: If URL format is invalid
        """
        return self.parser.extract_shortcode(url)

    def download(
        self,
        url: str,
        output_dir: Optional[Path] = None
    ) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download Instagram media.

        Args:
            url: Instagram URL
            output_dir: Output directory (ignored, uses settings.download_dir)

        Returns:
            Tuple of (media_path, thumbnail_path, metadata)

        Raises:
            ContentNotFoundError: Post not found
            PrivateAccountError: Private account
            DownloadFailedError: Download failed
        """
        shortcode = self.extract_identifier(url)
        logger.info(f"Downloading Instagram post: {shortcode}")

        return self.downloader.download(shortcode)

    def get_platform_info(self) -> dict:
        """Get Instagram platform information."""
        has_auth = bool(settings.instagram_username and settings.instagram_password)

        return {
            "platform": self.platform_name.value,
            "supported_types": ["video", "photo", "carousel", "reels"],
            "requires_auth": True,  # For full functionality
            "auth_configured": has_auth,
            "notes": "Free methods only download logos. Instagram account recommended."
        }
