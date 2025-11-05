"""Universal SNS downloader with platform routing.

Automatically detects platform from URL and routes to appropriate downloader.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, List

from app.models import MediaMetadata
from app.exceptions import DownloadFailedError
from app.platforms import BasePlatform, InstagramPlatform, YouTubePlatform

logger = logging.getLogger(__name__)


class UniversalDownloader:
    """Universal downloader supporting multiple SNS platforms."""

    def __init__(self):
        """Initialize universal downloader with all platforms."""
        self.platforms: List[BasePlatform] = [
            InstagramPlatform(),
            YouTubePlatform(),
            # Add more platforms here in the future:
            # TikTokPlatform(),
            # TwitterPlatform(),
        ]

        logger.info(f"Universal downloader initialized with {len(self.platforms)} platforms")

    def detect_platform(self, url: str) -> Optional[BasePlatform]:
        """Detect which platform can handle the given URL.

        Args:
            url: Social media URL

        Returns:
            Platform instance that can handle this URL, or None
        """
        for platform in self.platforms:
            if platform.can_handle(url):
                logger.info(f"Detected platform: {platform.platform_name.value}")
                return platform

        logger.warning(f"No platform found for URL: {url}")
        return None

    def download(
        self,
        url: str,
        output_dir: Optional[Path] = None
    ) -> Tuple[Path, Optional[Path], MediaMetadata, str]:
        """Download media from any supported platform.

        Args:
            url: Social media URL
            output_dir: Optional output directory

        Returns:
            Tuple of (media_path, thumbnail_path, metadata, platform_name)

        Raises:
            DownloadFailedError: If no platform can handle the URL
            Various platform-specific exceptions
        """
        platform = self.detect_platform(url)

        if not platform:
            # Try to provide helpful error message
            if 'instagram.com' in url:
                hint = "URL might be malformed. Check Instagram URL format."
            elif 'youtube.com' in url or 'youtu.be' in url:
                hint = "URL might be malformed. Check YouTube URL format."
            elif 'tiktok.com' in url:
                hint = "TikTok support coming soon!"
            elif 'twitter.com' in url or 'x.com' in url:
                hint = "Twitter/X support coming soon!"
            else:
                hint = "Supported platforms: Instagram, YouTube (more coming soon!)"

            raise DownloadFailedError(
                f"Unsupported URL or platform. {hint}",
                details={"url": url}
            )

        # Download using detected platform
        logger.info(f"Routing to {platform.platform_name.value} downloader")
        media_path, thumbnail_path, metadata = platform.download(url, output_dir)

        return media_path, thumbnail_path, metadata, platform.platform_name.value

    def get_supported_platforms(self) -> List[dict]:
        """Get information about all supported platforms.

        Returns:
            List of platform information dictionaries
        """
        return [platform.get_platform_info() for platform in self.platforms]

    def is_url_supported(self, url: str) -> bool:
        """Check if URL is supported by any platform.

        Args:
            url: Social media URL

        Returns:
            True if URL is supported
        """
        return self.detect_platform(url) is not None
