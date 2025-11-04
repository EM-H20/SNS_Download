"""Instagram media type detection before downloading.

Analyzes Instagram URLs to determine content type (video, photo, carousel)
without downloading the full media, enabling intelligent routing to the
appropriate downloader.
"""

import logging
from typing import Dict, Literal

import yt_dlp

from app.config import settings
from app.exceptions import (
    ContentNotFoundError,
    PrivateAccountError,
    InstagramAPIError,
    DownloadFailedError,
)

logger = logging.getLogger(__name__)

MediaType = Literal["video", "photo", "carousel"]


class InstagramMediaAnalyzer:
    """Analyze Instagram content type without downloading."""

    def __init__(self):
        """Initialize analyzer with minimal yt-dlp configuration."""
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,  # Only extract metadata
            'socket_timeout': settings.request_timeout_seconds,
            'http_headers': {
                'User-Agent': settings.user_agent,
            },
        }

    def analyze(self, shortcode: str) -> Dict[str, any]:
        """Analyze Instagram content type and metadata.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Dictionary with:
            - media_type: "video", "photo", or "carousel"
            - is_carousel: Boolean indicating if it's a carousel post
            - item_count: Number of items in carousel (1 for single media)
            - requires_login: Boolean indicating if Instaloader is needed
            - metadata: Raw info dict from yt-dlp

        Raises:
            ContentNotFoundError: Content doesn't exist
            PrivateAccountError: Content is private
            InstagramAPIError: Analysis failed
        """
        url = f"https://www.instagram.com/p/{shortcode}/"

        try:
            logger.info(f"Analyzing Instagram content: {shortcode}")

            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            # Check if it's a carousel/album
            is_carousel = info.get('_type') == 'playlist' or bool(info.get('entries'))
            item_count = len(info.get('entries', [])) if is_carousel else 1

            if is_carousel:
                logger.info(f"Detected carousel with {item_count} items: {shortcode}")
                # Get first entry to determine content type
                first_entry = info['entries'][0] if info.get('entries') else info
                is_video = self._is_video_content(first_entry)
                media_type = "carousel"
                # Carousel requires Instaloader for full download
                requires_login = True
            else:
                # Single media
                is_video = self._is_video_content(info)

                if is_video:
                    media_type = "video"
                    requires_login = False  # yt-dlp handles videos well
                else:
                    media_type = "photo"
                    # yt-dlp doesn't support Instagram photos
                    requires_login = True

            analysis = {
                "media_type": media_type,
                "is_carousel": is_carousel,
                "item_count": item_count,
                "requires_login": requires_login,
                "is_video": is_video if not is_carousel else None,
                "metadata": info
            }

            logger.info(
                f"Analysis complete: {shortcode} -> "
                f"{media_type}, items={item_count}, needs_login={requires_login}"
            )

            return analysis

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e).lower()

            if 'private' in error_msg or 'unavailable' in error_msg:
                logger.warning(f"Private or unavailable content: {shortcode}")
                raise PrivateAccountError(
                    "Content is private or unavailable",
                    details={"shortcode": shortcode}
                )

            if '404' in error_msg or 'not found' in error_msg:
                logger.warning(f"Content not found: {shortcode}")
                raise ContentNotFoundError(
                    "Content does not exist or has been deleted",
                    details={"shortcode": shortcode}
                )

            logger.error(f"Analysis failed for {shortcode}: {error_msg}")
            raise InstagramAPIError(
                "Failed to analyze Instagram content",
                details={"shortcode": shortcode, "error": error_msg}
            )

        except Exception as e:
            logger.exception(f"Unexpected error analyzing {shortcode}")
            raise DownloadFailedError(
                f"Analysis error: {str(e)}",
                details={"shortcode": shortcode, "error_type": type(e).__name__}
            )

    def _is_video_content(self, info: Dict) -> bool:
        """Determine if content is video based on metadata.

        Args:
            info: yt-dlp info dictionary

        Returns:
            True if video, False if photo
        """
        # Check file extension
        ext = info.get('ext', '').lower()
        if ext in ['mp4', 'webm', 'mov']:
            return True

        # Check video codec
        if info.get('vcodec') and info.get('vcodec') != 'none':
            return True

        # Check for duration (photos don't have duration)
        if info.get('duration') and info.get('duration') > 0:
            return True

        # Default to photo if no video indicators
        return False

    def recommend_downloader(self, shortcode: str) -> Literal["yt-dlp", "instaloader"]:
        """Recommend which downloader to use based on analysis.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            "yt-dlp" or "instaloader"
        """
        analysis = self.analyze(shortcode)

        if analysis["requires_login"]:
            return "instaloader"
        else:
            return "yt-dlp"
