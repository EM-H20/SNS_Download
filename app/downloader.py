"""Instagram media download engine using yt-dlp.

Switched from Instaloader to yt-dlp due to Instagram API 401 errors (Nov 2024).
yt-dlp handles Instagram's anti-bot measures better and is actively maintained.

Design considerations:
- yt-dlp handles TLS fingerprinting and browser emulation internally
- No authentication required for public posts
- Rate limiting is handled at application level
- Supports videos, photos, and Reels
"""

import logging
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

import yt_dlp

from app.config import settings
from app.exceptions import (
    PrivateAccountError,
    ContentNotFoundError,
    RateLimitExceededError,
    DownloadFailedError,
    InstagramAPIError,
)
from app.models import MediaMetadata

logger = logging.getLogger(__name__)


class ReelsDownloader:
    """Production-grade Instagram media downloader using yt-dlp."""

    def __init__(self):
        """Initialize yt-dlp with optimized settings for Instagram."""
        # Base configuration for yt-dlp
        self.base_ydl_opts = {
            'quiet': True,  # Suppress console output
            'no_warnings': True,  # Suppress warnings
            'extract_flat': False,  # Extract full metadata
            'socket_timeout': settings.request_timeout_seconds,
            'retries': settings.max_retries,
            # Custom user agent to avoid bot detection
            'http_headers': {
                'User-Agent': settings.user_agent,
            },
        }

        # Add Instagram authentication if credentials are provided
        # This enables downloading carousel posts and private content
        if settings.instagram_username and settings.instagram_password:
            self.base_ydl_opts['username'] = settings.instagram_username
            self.base_ydl_opts['password'] = settings.instagram_password
            logger.info(f"Instagram authentication enabled for user: {settings.instagram_username}")
        else:
            logger.info("Instagram authentication disabled - only public single media supported")

    def download(self, shortcode: str) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download Instagram media (video or photo) using shortcode.

        Args:
            shortcode: Instagram post shortcode (11 characters)

        Returns:
            Tuple of (media_path, thumbnail_path, metadata)
            - For videos: (video.mp4, thumbnail.jpg, metadata)
            - For photos: (photo.jpg, None, metadata)

        Raises:
            PrivateAccountError: Content is from a private account
            ContentNotFoundError: Content doesn't exist or was deleted
            RateLimitExceededError: Instagram rate limiting detected
            DownloadFailedError: Download failed after all retries
            InstagramAPIError: Instagram structure changed or other API errors
        """
        url = f"https://www.instagram.com/p/{shortcode}/"
        target_dir = settings.download_dir / shortcode
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Fetching Instagram content for shortcode: {shortcode}")

            # First, extract metadata without downloading
            info = self._extract_info(url)

            # Determine media type
            is_video = info.get('ext') in ['mp4', 'webm', 'mov'] or info.get('vcodec') != 'none'
            media_type = "video" if is_video else "photo"
            logger.info(f"Detected media type: {media_type} for shortcode: {shortcode}")

            # Download the media
            media_path = self._download_media(url, target_dir, shortcode, info)

            # Extract thumbnail if video
            thumbnail_path = None
            if is_video:
                thumbnail_path = self._download_thumbnail(info, target_dir, shortcode)

            # Build metadata
            metadata = MediaMetadata(
                shortcode=shortcode,
                duration_seconds=int(info.get('duration', 0)) if info.get('duration') else None,
                width=info.get('width'),
                height=info.get('height'),
                size_bytes=media_path.stat().st_size if media_path.exists() else None,
                download_timestamp=datetime.utcnow(),
            )

            logger.info(f"Download completed successfully: {shortcode} ({media_type})")
            return media_path, thumbnail_path, metadata

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            # Private account detection
            if 'private' in error_msg or 'unavailable' in error_msg:
                logger.warning(f"Private account or unavailable content: {shortcode}")
                raise PrivateAccountError(
                    f"Content is private or unavailable",
                    details={"shortcode": shortcode, "error": str(e)}
                )

            # Content not found
            if '404' in error_msg or 'not found' in error_msg or 'removed' in error_msg:
                logger.warning(f"Content not found: {shortcode}")
                raise ContentNotFoundError(
                    "Content does not exist or has been deleted",
                    details={"shortcode": shortcode}
                )

            # Rate limiting detection
            if '429' in error_msg or 'too many requests' in error_msg or 'rate limit' in error_msg:
                logger.warning(f"Rate limit detected for {shortcode}")
                raise RateLimitExceededError(
                    "Instagram rate limit exceeded, retry later",
                    details={"shortcode": shortcode, "retry_after_seconds": 300}
                )

            # API changes or other errors
            if 'http error' in error_msg or 'unable to extract' in error_msg:
                logger.error(f"Possible Instagram API change: {error_msg}")
                raise InstagramAPIError(
                    "Instagram may have changed their structure",
                    details={"shortcode": shortcode, "error": error_msg}
                )

            # Generic download failure
            logger.error(f"Download failed for {shortcode}: {error_msg}")
            raise DownloadFailedError(
                f"Failed to download content: {error_msg}",
                details={"shortcode": shortcode}
            )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(f"Unexpected error downloading {shortcode}")
            raise DownloadFailedError(
                f"Unexpected error during download: {str(e)}",
                details={"shortcode": shortcode, "error_type": type(e).__name__}
            )

    def _extract_info(self, url: str) -> Dict[str, Any]:
        """Extract metadata from Instagram URL without downloading.

        Returns:
            Dictionary with video/photo information
        """
        ydl_opts = {
            **self.base_ydl_opts,
            'skip_download': True,  # Only extract info
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    def _download_media(
        self,
        url: str,
        target_dir: Path,
        shortcode: str,
        info: Dict[str, Any]
    ) -> Path:
        """Download the actual media file (video or photo).

        Returns:
            Path to downloaded media file
        """
        # Configure output template to include date and shortcode
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_template = str(target_dir / f"{date_str}_{shortcode}.%(ext)s")

        ydl_opts = {
            **self.base_ydl_opts,
            'outtmpl': output_template,
            'format': 'best',  # Download best quality
        }

        logger.info(f"Downloading media to {target_dir}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find the downloaded file
        # yt-dlp will use the extension from the video (.mp4, .jpg, etc.)
        possible_extensions = ['mp4', 'webm', 'mov', 'jpg', 'jpeg', 'png']
        for ext in possible_extensions:
            media_file = target_dir / f"{date_str}_{shortcode}.{ext}"
            if media_file.exists():
                logger.info(f"Media file found: {media_file}")
                return media_file

        # If not found with expected naming, search directory
        media_files = list(target_dir.glob(f"*{shortcode}*"))
        if media_files:
            logger.warning(f"Using alternative file: {media_files[0]}")
            return media_files[0]

        raise DownloadFailedError(
            "Media file not found after download",
            details={"directory": str(target_dir), "shortcode": shortcode}
        )

    def _download_thumbnail(
        self,
        info: Dict[str, Any],
        target_dir: Path,
        shortcode: str
    ) -> Optional[Path]:
        """Download thumbnail for video content.

        Returns:
            Path to thumbnail file, or None if unavailable
        """
        thumbnail_url = info.get('thumbnail')
        if not thumbnail_url:
            logger.debug(f"No thumbnail available for {shortcode}")
            return None

        try:
            import requests
            from io import BytesIO
            from PIL import Image

            # Download thumbnail
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()

            # Save as JPG
            date_str = datetime.now().strftime('%Y-%m-%d')
            thumbnail_path = target_dir / f"{date_str}_{shortcode}_thumb.jpg"

            # Convert to JPG if needed
            img = Image.open(BytesIO(response.content))
            img = img.convert('RGB')  # Ensure RGB mode
            img.save(thumbnail_path, 'JPEG', quality=90)

            logger.info(f"Thumbnail saved: {thumbnail_path}")
            return thumbnail_path

        except Exception as e:
            logger.warning(f"Failed to download thumbnail: {e}")
            return None
