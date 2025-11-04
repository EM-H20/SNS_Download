"""Instagram Reels download engine with multiple fallback strategies.

Primary: Instaloader (Python library, fast, no browser overhead)
Fallback: Could be extended with Playwright for resilience

Design considerations:
- Instaloader requires no authentication for public posts
- Rate limiting is handled at application level, not here
- Error handling distinguishes between retryable and permanent failures
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

import instaloader
from instaloader.exceptions import (
    InstaloaderException,
    ProfileNotExistsException,
    PostChangedException,
    LoginRequiredException,
)

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
    """Production-grade Instagram Reels downloader with error handling."""

    def __init__(self):
        """Initialize Instaloader with optimized settings."""
        self.loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=True,
            download_pictures=True,  # Enable photo downloads
            download_comments=False,  # We only need media files
            download_geotags=False,
            save_metadata=False,  # Skip JSON metadata to reduce I/O
            compress_json=False,
            post_metadata_txt_pattern='',  # Disable txt file generation
            max_connection_attempts=settings.max_retries,
        )

        # Configure user agent to avoid detection as bot
        self.loader.context.user_agent = settings.user_agent

    def download(self, shortcode: str) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download Instagram media (video or photo) and thumbnail using shortcode.

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
            InstagramAPIError: Instagram API structure changed
        """
        try:
            logger.info(f"Fetching post metadata for shortcode: {shortcode}")
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            # Log media type for debugging
            media_type = "video" if post.is_video else "photo"
            logger.info(f"Detected media type: {media_type} for shortcode: {shortcode}")

            # Check if post is accessible (public account)
            if post.owner_profile.is_private:
                raise PrivateAccountError(
                    f"Cannot download from private account: @{post.owner_profile.username}",
                    details={"username": post.owner_profile.username}
                )

            # Download to configured directory
            target_dir = settings.download_dir / shortcode
            target_dir.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading {media_type} to {target_dir}")
            self.loader.download_post(post, target=str(target_dir))

            # Locate downloaded files based on media type
            if post.is_video:
                media_path = self._find_video_file(target_dir, shortcode)
                thumbnail_path = self._find_thumbnail_file(target_dir, shortcode)
            else:
                # For photos, the main image is the media, no separate thumbnail
                media_path = self._find_image_file(target_dir, shortcode)
                thumbnail_path = None  # Photos don't have separate thumbnails

            # Extract metadata for response
            metadata = MediaMetadata(
                shortcode=shortcode,
                duration_seconds=post.video_duration if post.is_video else None,
                width=post.dimensions[0] if post.dimensions else None,
                height=post.dimensions[1] if post.dimensions else None,
                size_bytes=media_path.stat().st_size if media_path else None,
                download_timestamp=datetime.utcnow(),
            )

            logger.info(f"Download completed successfully: {shortcode} ({media_type})")
            return media_path, thumbnail_path, metadata

        except LoginRequiredException as e:
            # This shouldn't happen for public posts, indicates API change
            logger.error(f"Unexpected login requirement for public post: {shortcode}")
            raise PrivateAccountError(
                "Content requires authentication (private account or API change)",
                details={"shortcode": shortcode, "original_error": str(e)}
            )

        except (ProfileNotExistsException, PostChangedException) as e:
            logger.warning(f"Content not found: {shortcode} - {str(e)}")
            raise ContentNotFoundError(
                "Content does not exist or has been deleted",
                details={"shortcode": shortcode}
            )

        except InstaloaderException as e:
            error_msg = str(e).lower()

            # Detect rate limiting patterns
            if "429" in error_msg or "too many requests" in error_msg:
                logger.warning(f"Rate limit detected for {shortcode}")
                raise RateLimitExceededError(
                    "Instagram rate limit exceeded, retry later",
                    details={"shortcode": shortcode, "retry_after_seconds": 300}
                )

            # Detect API structure changes
            if "json" in error_msg or "graphql" in error_msg:
                logger.error(f"Possible Instagram API change: {error_msg}")
                raise InstagramAPIError(
                    "Instagram API structure may have changed",
                    details={"shortcode": shortcode, "error": error_msg}
                )

            # Generic Instaloader failure
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

    def _find_video_file(self, directory: Path, shortcode: str) -> Optional[Path]:
        """Locate the video file in download directory.

        Instaloader naming: {date}_{shortcode}.mp4
        """
        video_files = list(directory.glob(f"*{shortcode}*.mp4"))
        if not video_files:
            logger.error(f"Video file not found in {directory}")
            raise DownloadFailedError(
                "Video file not found after download",
                details={"directory": str(directory), "shortcode": shortcode}
            )
        return video_files[0]  # Return first match

    def _find_thumbnail_file(self, directory: Path, shortcode: str) -> Optional[Path]:
        """Locate the thumbnail file in download directory.

        Instaloader naming: {date}_{shortcode}.jpg
        For videos, this is the video thumbnail.
        """
        thumbnail_files = list(directory.glob(f"*{shortcode}*.jpg"))
        return thumbnail_files[0] if thumbnail_files else None

    def _find_image_file(self, directory: Path, shortcode: str) -> Optional[Path]:
        """Locate the image file for photo posts.

        Instaloader naming: {date}_{shortcode}.jpg
        For photos, this is the main image.
        """
        image_files = list(directory.glob(f"*{shortcode}*.jpg"))
        if not image_files:
            logger.error(f"Image file not found in {directory}")
            raise DownloadFailedError(
                "Image file not found after download",
                details={"directory": str(directory), "shortcode": shortcode}
            )
        return image_files[0]  # Return first match
