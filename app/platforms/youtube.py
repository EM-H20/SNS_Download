"""YouTube platform downloader using yt-dlp.

Supports:
- YouTube videos
- YouTube Shorts
- YouTube live streams (VOD)
"""

import logging
import re
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

import yt_dlp

from app.config import settings
from app.models import MediaMetadata
from app.exceptions import ContentNotFoundError, DownloadFailedError
from .base import BasePlatform, PlatformType

logger = logging.getLogger(__name__)


class YouTubePlatform(BasePlatform):
    """YouTube downloader using yt-dlp."""

    @property
    def platform_name(self) -> PlatformType:
        return PlatformType.YOUTUBE

    def can_handle(self, url: str) -> bool:
        """Check if URL is from YouTube.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID
        """
        youtube_patterns = [
            r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+',
            r'(?:https?://)?youtu\.be/[\w-]+',
            r'(?:https?://)?m\.youtube\.com/watch\?v=[\w-]+',
        ]

        return any(re.match(pattern, url) for pattern in youtube_patterns)

    def extract_identifier(self, url: str) -> str:
        """Extract video ID from YouTube URL.

        Args:
            url: YouTube URL

        Returns:
            Video ID (11 characters)

        Raises:
            ValueError: If URL format is invalid
        """
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([\w-]{11})',
            r'(?:m\.youtube\.com/watch\?v=)([\w-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise ValueError(f"Invalid YouTube URL format: {url}")

    def download(
        self,
        url: str,
        output_dir: Optional[Path] = None
    ) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download YouTube video or short.

        Args:
            url: YouTube URL
            output_dir: Output directory (defaults to settings.download_dir)

        Returns:
            Tuple of (video_path, thumbnail_path, metadata)

        Raises:
            ContentNotFoundError: Video not found or private
            DownloadFailedError: Download failed
        """
        if output_dir is None:
            output_dir = settings.download_dir

        video_id = self.extract_identifier(url)
        target_dir = output_dir / f"youtube_{video_id}"
        target_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading YouTube video: {video_id}")

        # Configure yt-dlp options
        date_str = datetime.now().strftime('%Y-%m-%d')
        output_template = str(target_dir / f"{date_str}_{video_id}.%(ext)s")

        ydl_opts = {
            'format': 'best[ext=mp4]/best',  # Prefer MP4
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': settings.request_timeout_seconds,
            'retries': settings.max_retries,
            'writethumbnail': True,  # Download thumbnail
            'http_headers': {
                'User-Agent': settings.user_agent,
            },
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first
                logger.info("Extracting video information...")
                info = ydl.extract_info(url, download=False)

                if not info:
                    raise ContentNotFoundError(
                        "Video not found or unavailable",
                        details={"video_id": video_id, "url": url}
                    )

                # Check if video is available
                if info.get('is_live') and not info.get('is_live_ended'):
                    raise DownloadFailedError(
                        "Cannot download live streams",
                        details={"video_id": video_id}
                    )

                # Download video
                logger.info("Downloading video...")
                ydl.download([url])

                # Find downloaded files
                video_path = None
                thumbnail_path = None

                for file in target_dir.iterdir():
                    if file.suffix in ['.mp4', '.webm', '.mkv']:
                        video_path = file
                    elif file.suffix in ['.jpg', '.png', '.webp']:
                        thumbnail_path = file

                if not video_path or not video_path.exists():
                    raise DownloadFailedError(
                        "Video file not found after download",
                        details={"video_id": video_id, "target_dir": str(target_dir)}
                    )

                # Build metadata
                metadata = MediaMetadata(
                    shortcode=video_id,
                    duration_seconds=info.get('duration'),
                    width=info.get('width'),
                    height=info.get('height'),
                    size_bytes=video_path.stat().st_size,
                    download_timestamp=datetime.utcnow(),
                )

                logger.info(
                    f"YouTube download successful: {video_path.name} "
                    f"({metadata.size_bytes:,} bytes, {metadata.duration_seconds}s)"
                )

                return video_path, thumbnail_path, metadata

        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)

            if 'Video unavailable' in error_msg or 'Private video' in error_msg:
                raise ContentNotFoundError(
                    "Video not found, private, or unavailable",
                    details={"video_id": video_id, "error": error_msg}
                )
            else:
                raise DownloadFailedError(
                    f"YouTube download failed: {error_msg}",
                    details={"video_id": video_id}
                )

        except Exception as e:
            logger.exception(f"Unexpected error downloading YouTube video {video_id}")
            raise DownloadFailedError(
                f"YouTube download failed: {str(e)}",
                details={"video_id": video_id}
            )

    def get_platform_info(self) -> dict:
        """Get YouTube platform information."""
        return {
            "platform": self.platform_name.value,
            "supported_types": ["video", "shorts", "live_vod"],
            "requires_auth": False,
            "max_quality": "best available",
        }
