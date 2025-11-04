"""Intelligent Instagram downloader router.

Routes download requests to the appropriate downloader based on media type:
- yt-dlp: For video Reels and video posts (no login required)
- Instaloader: For photo posts and carousel posts (requires login)
"""

import logging
from pathlib import Path
from typing import Tuple, Optional, List, Union

from app.config import settings
from app.media_analyzer import InstagramMediaAnalyzer
from app.downloader import ReelsDownloader
from app.downloader_instaloader import InstaloaderDownloader
from app.models import MediaMetadata
from app.exceptions import (
    DownloadFailedError,
    InstagramAPIError,
)

logger = logging.getLogger(__name__)


class InstagramDownloaderRouter:
    """Routes Instagram downloads to the optimal downloader."""

    def __init__(self):
        """Initialize router with both downloaders and analyzer."""
        self.analyzer = InstagramMediaAnalyzer()
        self.yt_dlp_downloader = ReelsDownloader()
        self.instaloader_downloader = None  # Lazy initialization

        # Check if Instagram credentials are available
        self.has_credentials = bool(
            settings.instagram_username and settings.instagram_password
        )

        if self.has_credentials:
            logger.info("Instagram credentials available - full feature support enabled")
        else:
            logger.warning(
                "Instagram credentials not configured - "
                "photo posts and carousel downloads disabled"
            )

    def download(self, shortcode: str) -> Tuple[Union[Path, List[Path]], Optional[Path], MediaMetadata, str]:
        """Download Instagram content using the appropriate downloader.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Tuple of (media_path(s), thumbnail_path, metadata, media_type)
            - For single media: (Path, Optional[Path], MediaMetadata, str)
            - For carousel: (List[Path], None, MediaMetadata, str)

        Raises:
            DownloadFailedError: If download fails or required features unavailable
            InstagramAPIError: If Instagram API errors occur
        """
        logger.info(f"Routing download request for shortcode: {shortcode}")

        # Analyze content to determine routing
        analysis = self.analyzer.analyze(shortcode)
        media_type = analysis["media_type"]
        requires_login = analysis["requires_login"]
        is_carousel = analysis["is_carousel"]

        logger.info(
            f"Routing decision: type={media_type}, "
            f"requires_login={requires_login}, carousel={is_carousel}"
        )

        # Route based on analysis
        if requires_login:
            # Photo or carousel - needs Instaloader
            if not self.has_credentials:
                # Provide helpful error message
                error_msg = self._get_credential_error_message(media_type, is_carousel)
                logger.error(f"Download blocked: {error_msg}")
                raise DownloadFailedError(
                    error_msg,
                    details={
                        "shortcode": shortcode,
                        "media_type": media_type,
                        "is_carousel": is_carousel,
                        "solution": "Configure INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env file"
                    }
                )

            # Use Instaloader
            logger.info(f"Using Instaloader for {media_type}: {shortcode}")
            return self._download_with_instaloader(shortcode, media_type)

        else:
            # Video - use yt-dlp
            logger.info(f"Using yt-dlp for video: {shortcode}")
            return self._download_with_ytdlp(shortcode)

    def _download_with_ytdlp(self, shortcode: str) -> Tuple[Path, Optional[Path], MediaMetadata, str]:
        """Download using yt-dlp (videos only).

        Returns:
            (media_path, thumbnail_path, metadata, media_type)
        """
        media_path, thumbnail_path, metadata = self.yt_dlp_downloader.download(shortcode)

        # Determine media type from extension
        media_type = "video" if media_path.suffix.lower() == ".mp4" else "photo"

        return media_path, thumbnail_path, metadata, media_type

    def _download_with_instaloader(self, shortcode: str, media_type: str) -> Tuple[Union[Path, List[Path]], Optional[Path], MediaMetadata, str]:
        """Download using Instaloader (photos and carousels).

        Returns:
            (media_paths, thumbnail_path, metadata, media_type)
        """
        # Lazy initialize Instaloader (only when needed)
        if self.instaloader_downloader is None:
            logger.info("Initializing Instaloader downloader")
            self.instaloader_downloader = InstaloaderDownloader()

        media_paths, thumbnail_path, metadata = self.instaloader_downloader.download(shortcode)

        # For single photo, return single path instead of list for consistency
        if len(media_paths) == 1 and media_type == "photo":
            return media_paths[0], thumbnail_path, metadata, media_type

        # For carousel, return list of paths
        return media_paths, thumbnail_path, metadata, media_type

    def _get_credential_error_message(self, media_type: str, is_carousel: bool) -> str:
        """Generate helpful error message for credential requirements.

        Args:
            media_type: Type of media being requested
            is_carousel: Whether it's a carousel post

        Returns:
            User-friendly error message
        """
        if is_carousel:
            return (
                "This is a carousel post with multiple items. "
                "yt-dlp can only download the first item. "
                "To download all items, configure Instagram credentials in .env file:\n"
                "INSTAGRAM_USERNAME=your_username\n"
                "INSTAGRAM_PASSWORD=your_password\n"
                "See CAROUSEL_SUPPORT.md for details."
            )
        elif media_type == "photo":
            return (
                "This is a photo post. yt-dlp does not support Instagram photos. "
                "To download photos, configure Instagram credentials in .env file:\n"
                "INSTAGRAM_USERNAME=your_username\n"
                "INSTAGRAM_PASSWORD=your_password\n"
                "Warning: Use a test account, not your main account."
            )
        else:
            return (
                "This content requires Instagram authentication. "
                "Configure credentials in .env file to enable this feature."
            )

    def get_capabilities(self) -> dict:
        """Get current router capabilities based on configuration.

        Returns:
            Dictionary describing what features are available
        """
        return {
            "video_reels": True,  # Always supported via yt-dlp
            "video_posts": True,  # Always supported via yt-dlp
            "photo_posts": self.has_credentials,  # Requires Instaloader
            "carousel_full": self.has_credentials,  # Requires Instaloader
            "carousel_first_item": True,  # yt-dlp can download first item
            "requires_authentication": not self.has_credentials,
            "authenticated": self.has_credentials,
        }
