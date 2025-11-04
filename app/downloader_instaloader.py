"""Instagram media download engine using Instaloader with login support.

Instaloader provides better carousel support and authentication handling.
This downloader is used when Instagram credentials are provided.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime

import instaloader

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


class InstaloaderDownloader:
    """Instagram downloader using Instaloader with authentication support."""

    def __init__(self):
        """Initialize Instaloader with optional login."""
        # Configure Instaloader
        # Why these settings: Minimize unnecessary downloads, focus on media only
        self.loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=True,
            download_pictures=True,
            download_comments=False,  # We don't need comments
            download_geotags=False,   # We don't need location data
            save_metadata=False,       # We don't need JSON metadata
            compress_json=False,
            post_metadata_txt_pattern='',  # No text files
            max_connection_attempts=settings.max_retries,
            quiet=True,  # Suppress output
        )

        # Set custom user agent to avoid bot detection
        self.loader.context.user_agent = settings.user_agent

        # Login if credentials are provided
        # Why: Enables carousel download and private content access
        if settings.instagram_username and settings.instagram_password:
            try:
                logger.info(f"Attempting Instagram login as: {settings.instagram_username}")
                self.loader.login(
                    settings.instagram_username,
                    settings.instagram_password
                )
                logger.info(f"Instagram login successful: {settings.instagram_username}")
                self.is_logged_in = True
            except Exception as e:
                logger.warning(f"Instagram login failed: {e}. Continuing without login.")
                self.is_logged_in = False
        else:
            logger.info("No Instagram credentials provided - carousel support disabled")
            self.is_logged_in = False

    def download(self, shortcode: str) -> Tuple[List[Path], Optional[Path], MediaMetadata]:
        """Download Instagram media using Instaloader.

        Args:
            shortcode: Instagram post shortcode (11 characters)

        Returns:
            Tuple of (media_paths, thumbnail_path, metadata)
            - For single media: ([video.mp4], thumbnail.jpg, metadata)
            - For carousel: ([photo1.jpg, photo2.jpg, ...], None, metadata)

        Raises:
            PrivateAccountError: Content is from a private account
            ContentNotFoundError: Content doesn't exist or was deleted
            RateLimitExceededError: Instagram rate limiting detected
            DownloadFailedError: Download failed after all retries
            InstagramAPIError: Instagram structure changed or other API errors
        """
        target_dir = settings.download_dir / shortcode
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Fetching Instagram content with Instaloader: {shortcode}")

            # Get post object from Instagram
            # Why: Instaloader handles authentication and rate limiting automatically
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)

            # Download the post
            # Why: Instaloader downloads all media in carousel automatically
            logger.info(f"Downloading post: {shortcode}")
            self.loader.download_post(post, target=str(target_dir))

            # Determine media type and find downloaded files
            is_carousel = post.typename == 'GraphSidecar'
            is_video = post.is_video

            if is_carousel:
                media_type = "carousel"
                logger.info(f"Detected carousel with {post.mediacount} items")
            elif is_video:
                media_type = "video"
                logger.info(f"Detected single video")
            else:
                media_type = "photo"
                logger.info(f"Detected single photo")

            # Find and organize downloaded files
            # Why: Instaloader creates multiple files, we need to find the actual media
            media_paths = self._find_media_files(target_dir, shortcode)

            if not media_paths:
                raise DownloadFailedError(
                    "No media files found after download",
                    details={"directory": str(target_dir), "shortcode": shortcode}
                )

            # Rename files to simple format: 2025-11-04_{shortcode}_1.jpg, etc.
            media_paths = self._rename_media_files(media_paths, target_dir, shortcode)

            # Find thumbnail for videos
            thumbnail_path = None
            if is_video and not is_carousel:
                thumbnail_path = self._find_thumbnail_file(target_dir, shortcode)

            # Build metadata
            metadata = MediaMetadata(
                shortcode=shortcode,
                duration_seconds=post.video_duration if is_video else None,
                width=None,  # Instaloader doesn't provide dimensions directly
                height=None,
                size_bytes=sum(p.stat().st_size for p in media_paths) if media_paths else None,
                download_timestamp=datetime.utcnow(),
            )

            logger.info(f"Download completed: {shortcode} ({media_type}, {len(media_paths)} files)")
            return media_paths, thumbnail_path, metadata

        except instaloader.exceptions.ProfileNotExistsException:
            logger.warning(f"Content not found: {shortcode}")
            raise ContentNotFoundError(
                "Content does not exist or has been deleted",
                details={"shortcode": shortcode}
            )

        except instaloader.exceptions.PrivateProfileNotFollowedException:
            logger.warning(f"Private account: {shortcode}")
            raise PrivateAccountError(
                "Content is from a private account",
                details={"shortcode": shortcode}
            )

        except instaloader.exceptions.TooManyRequestsException:
            logger.warning(f"Rate limit detected for {shortcode}")
            raise RateLimitExceededError(
                "Instagram rate limit exceeded, retry later",
                details={"shortcode": shortcode, "retry_after_seconds": 300}
            )

        except instaloader.exceptions.ConnectionException as e:
            error_msg = str(e).lower()

            # Check for specific error types
            if '401' in error_msg or 'unauthorized' in error_msg:
                logger.error(f"Instagram API 401 error: {error_msg}")
                raise InstagramAPIError(
                    "Instagram authentication required or API changed",
                    details={"shortcode": shortcode, "error": error_msg}
                )

            if '404' in error_msg or 'not found' in error_msg:
                logger.warning(f"Content not found: {shortcode}")
                raise ContentNotFoundError(
                    "Content does not exist or has been deleted",
                    details={"shortcode": shortcode}
                )

            # Generic connection error
            logger.error(f"Connection error downloading {shortcode}: {error_msg}")
            raise DownloadFailedError(
                f"Connection error: {error_msg}",
                details={"shortcode": shortcode}
            )

        except Exception as e:
            # Catch-all for unexpected errors
            logger.exception(f"Unexpected error downloading {shortcode}")
            raise DownloadFailedError(
                f"Unexpected error during download: {str(e)}",
                details={"shortcode": shortcode, "error_type": type(e).__name__}
            )

    def _find_media_files(self, target_dir: Path, shortcode: str) -> List[Path]:
        """Find all media files downloaded by Instaloader.

        Why: Instaloader creates files with timestamp prefix, we need to find them.
        """
        # Instaloader creates files like: 2024-11-04_12-34-56_UTC.jpg
        # Look for common image and video extensions
        media_files = []

        for ext in ['jpg', 'jpeg', 'png', 'mp4', 'webm', 'mov']:
            files = list(target_dir.glob(f"*.{ext}"))
            # Filter out thumbnails (contain '_thumb' in filename)
            files = [f for f in files if '_thumb' not in f.name.lower()]
            media_files.extend(files)

        # Sort by creation time to maintain order
        media_files.sort(key=lambda p: p.stat().st_ctime)

        return media_files

    def _find_thumbnail_file(self, target_dir: Path, shortcode: str) -> Optional[Path]:
        """Find thumbnail file for video."""
        # Look for files with 'thumb' in the name
        thumb_files = list(target_dir.glob("*thumb*.jpg"))
        return thumb_files[0] if thumb_files else None

    def _rename_media_files(self, media_paths: List[Path], target_dir: Path, shortcode: str) -> List[Path]:
        """Rename media files to simple format.

        Why: Make file names predictable and easy to use.
        Format: 2025-11-04_{shortcode}_1.jpg, 2025-11-04_{shortcode}_2.jpg, etc.
        """
        date_str = datetime.now().strftime('%Y-%m-%d')
        renamed_paths = []

        for idx, media_path in enumerate(media_paths, 1):
            ext = media_path.suffix
            if len(media_paths) == 1:
                # Single file: 2025-11-04_{shortcode}.jpg
                new_name = f"{date_str}_{shortcode}{ext}"
            else:
                # Multiple files: 2025-11-04_{shortcode}_1.jpg, etc.
                new_name = f"{date_str}_{shortcode}_{idx}{ext}"

            new_path = target_dir / new_name

            # Only rename if different
            if media_path != new_path:
                # Remove destination if exists
                if new_path.exists():
                    new_path.unlink()
                media_path.rename(new_path)
                renamed_paths.append(new_path)
            else:
                renamed_paths.append(media_path)

        return renamed_paths

    def cleanup_temp_files(self, target_dir: Path):
        """Clean up temporary files created by Instaloader.

        Why: Instaloader creates extra metadata files we don't need.
        """
        # Remove .txt metadata files
        for txt_file in target_dir.glob("*.txt"):
            txt_file.unlink()

        # Remove .json.xz compressed metadata
        for json_file in target_dir.glob("*.json*"):
            json_file.unlink()
