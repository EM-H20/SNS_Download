"""Instagram media download engine with multiple fallback strategies.

Hybrid approach for maximum compatibility:
1. Proxy/Embed method (no auth) - Fast, works for public content
2. yt-dlp (optional auth) - Fallback for videos
3. Instaloader (requires auth) - Full feature support

Design considerations:
- Try non-auth methods first for speed and simplicity
- Fall back to authenticated methods when needed
- Rate limiting is handled at application level
- Supports videos, photos, and carousel posts
"""

import logging
import json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

import yt_dlp
import requests
from PIL import Image
from io import BytesIO

from app.config import settings, account_manager
from app.exceptions import (
    PrivateAccountError,
    ContentNotFoundError,
    RateLimitExceededError,
    DownloadFailedError,
    InstagramAPIError,
)
from app.models import MediaMetadata
from app.metadata_extractor import InstagramMetadataExtractor
from app.metadata_storage import MetadataStorage
from app.instagram_proxy import InstagramProxyDownloader

logger = logging.getLogger(__name__)


class ReelsDownloader:
    """Production-grade Instagram media downloader with fallback strategies."""

    def __init__(self):
        """Initialize downloader with multiple strategies."""
        # Strategy 1: Proxy downloader (no auth required)
        self.proxy_downloader = InstagramProxyDownloader()

        # Check if account manager is available (다중 계정 지원)
        self.has_auth = account_manager is not None and account_manager.has_available_accounts()

        if self.has_auth:
            logger.info(f"Instagram authentication enabled with {len(account_manager.accounts)} account(s)")
        else:
            logger.info("No authentication - using proxy/embed methods for public content")

        # Current account for this download (will be set per-request)
        self.current_account = None

    def _check_existing_download(
        self,
        shortcode: str,
        target_dir: Path
    ) -> Optional[Tuple[Path, Optional[Path], MediaMetadata]]:
        """기존 다운로드 파일 체크 (중복 다운로드 방지).

        Args:
            shortcode: Instagram shortcode
            target_dir: Target directory

        Returns:
            기존 파일이 있으면 (media_path, thumbnail_path, metadata), 없으면 None
        """
        # shortcode 패턴으로 미디어 파일 검색
        possible_extensions = ['mp4', 'webm', 'mov', 'jpg', 'jpeg', 'png']

        for ext in possible_extensions:
            media_files = list(target_dir.glob(f"*{shortcode}.{ext}"))
            if media_files:
                media_path = media_files[0]

                # 썸네일 찾기
                thumbnail_path = None
                thumbnail_patterns = [
                    target_dir / f"*{shortcode}_thumb.jpg",
                    target_dir / f"*{shortcode}_thumb.jpeg",
                    target_dir / f"*{shortcode}.webp",
                ]
                for pattern in thumbnail_patterns:
                    thumbs = list(target_dir.glob(pattern.name))
                    if thumbs:
                        thumbnail_path = thumbs[0]
                        break

                # 메타데이터 생성
                is_video = ext in ['mp4', 'webm', 'mov']
                metadata = MediaMetadata(
                    shortcode=shortcode,
                    duration_seconds=None,
                    width=None,
                    height=None,
                    size_bytes=media_path.stat().st_size if media_path.exists() else None,
                    download_timestamp=datetime.fromtimestamp(media_path.stat().st_mtime) if media_path.exists() else datetime.utcnow(),
                )

                logger.info(f"Found existing file: {media_path} ({metadata.size_bytes / (1024*1024):.1f}MB)")
                return media_path, thumbnail_path, metadata

        # 기존 파일 없음
        return None

    def download(self, shortcode: str) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download Instagram media using best available method.

        Strategy:
        1. Try proxy/embed method (no auth, fast)
        2. Fall back to yt-dlp if available
        3. Fall back to Instaloader if credentials provided

        Args:
            shortcode: Instagram post shortcode (8-15 characters)

        Returns:
            Tuple of (media_path, thumbnail_path, metadata)

        Raises:
            PrivateAccountError: Content is from a private account
            ContentNotFoundError: Content doesn't exist or was deleted
            RateLimitExceededError: Instagram rate limiting detected
            DownloadFailedError: All download methods failed
        """
        target_dir = settings.download_dir / shortcode
        target_dir.mkdir(parents=True, exist_ok=True)

        # 중복 다운로드 체크 (이미 다운로드된 파일이 있으면 재사용)
        existing_media = self._check_existing_download(shortcode, target_dir)
        if existing_media:
            media_path, thumbnail_path, metadata = existing_media
            logger.info(f"Using existing download for shortcode: {shortcode} (skip re-download)")
            return media_path, thumbnail_path, metadata

        logger.info(f"Starting download for shortcode: {shortcode}")

        # Strategy 1: Try yt-dlp with auth first (BEST QUALITY)
        if self.has_auth:
            # 랜덤 계정 선택 (차단 우회)
            self.current_account = account_manager.get_random_account()

            if self.current_account:
                try:
                    logger.info(f"Trying yt-dlp with account: {self.current_account.username}")
                    result = self._download_via_ytdlp(shortcode, target_dir)

                    # 성공 기록
                    account_manager.mark_account_success(self.current_account.username)
                    return result

                except Exception as e:
                    logger.warning(f"yt-dlp method failed with {self.current_account.username}: {e}")

                    # 실패 기록 (차단 감지 시 자동으로 해당 계정 일시 차단)
                    account_manager.mark_account_failure(self.current_account.username)
            else:
                logger.warning("No available Instagram accounts (all blocked)")

        # Strategy 2: Fallback to proxy/embed method (NO AUTH REQUIRED)
        try:
            logger.info("Trying proxy/embed method (no authentication)...")
            return self._download_via_proxy(shortcode, target_dir)
        except Exception as e:
            logger.warning(f"Proxy method failed: {e}")

        # All methods failed
        raise DownloadFailedError(
            "All download methods failed. Content may be private or Instagram blocking access.",
            details={"shortcode": shortcode}
        )

    def _download_via_proxy(self, shortcode: str, target_dir: Path) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download using proxy/embed method (no authentication).

        Args:
            shortcode: Post shortcode
            target_dir: Target directory

        Returns:
            Tuple of (media_path, thumbnail_path, metadata)
        """
        # Get media URLs from proxy
        data = self.proxy_downloader.get_media_urls(shortcode)

        if not data or 'media_urls' not in data:
            raise DownloadFailedError("No media URLs found")

        # Download first media URL (main image/video)
        media_urls = data['media_urls']
        if not media_urls:
            raise DownloadFailedError("Empty media URLs list")

        # Determine file extension
        main_url = media_urls[0]
        if '.mp4' in main_url:
            ext = 'mp4'
            is_video = True
        elif '.jpg' in main_url or 'jpg' in main_url:
            ext = 'jpg'
            is_video = False
        elif '.png' in main_url:
            ext = 'png'
            is_video = False
        else:
            ext = 'jpg'  # Default
            is_video = False

        # Create filename
        date_str = datetime.now().strftime('%Y-%m-%d')
        media_filename = f"{date_str}_{shortcode}.{ext}"
        media_path = target_dir / media_filename

        # Download media
        logger.info(f"Downloading from CDN: {main_url[:80]}...")
        self.proxy_downloader.download_media(main_url, str(media_path))

        # Download thumbnail if available (second URL is usually thumbnail)
        thumbnail_path = None
        if len(media_urls) > 1 and is_video:
            thumb_url = media_urls[1]
            thumbnail_filename = f"{date_str}_{shortcode}_thumb.jpg"
            thumbnail_path = target_dir / thumbnail_filename

            try:
                self.proxy_downloader.download_media(thumb_url, str(thumbnail_path))
            except Exception as e:
                logger.warning(f"Failed to download thumbnail: {e}")
                thumbnail_path = None

        # Build metadata
        metadata = MediaMetadata(
            shortcode=shortcode,
            duration_seconds=None,
            width=None,
            height=None,
            size_bytes=media_path.stat().st_size if media_path.exists() else None,
            download_timestamp=datetime.utcnow(),
        )

        logger.info(f"Proxy download successful: {media_path}")
        return media_path, thumbnail_path, metadata

    def _download_via_ytdlp(self, shortcode: str, target_dir: Path) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download using yt-dlp (fallback method).

        Args:
            shortcode: Post shortcode
            target_dir: Target directory

        Returns:
            Tuple of (media_path, thumbnail_path, metadata)
        """
        url = f"https://www.instagram.com/p/{shortcode}/"

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

            # Extract and save text metadata if enabled
            if settings.save_metadata:
                try:
                    logger.info(f"Extracting text metadata for {shortcode}")
                    text_metadata = InstagramMetadataExtractor.extract_from_ytdlp(info, shortcode)
                    MetadataStorage.save_metadata(shortcode, text_metadata)
                except Exception as e:
                    logger.warning(f"Failed to save text metadata: {e}")

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

    def _get_ydl_opts(self) -> Dict[str, Any]:
        """yt-dlp 옵션 생성 (현재 계정 및 랜덤 USER_AGENT 적용).

        Returns:
            yt-dlp 옵션 딕셔너리
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': settings.request_timeout_seconds,
            'retries': settings.max_retries,
            'max_filesize': settings.max_file_size_mb * 1024 * 1024,
            'http_headers': {
                'User-Agent': settings.get_random_user_agent(),  # 매 요청마다 랜덤 USER_AGENT
            },
        }

        # 현재 선택된 계정 정보 추가
        if self.current_account:
            ydl_opts['username'] = self.current_account.username
            ydl_opts['password'] = self.current_account.password

        return ydl_opts

    def _extract_info(self, url: str) -> Dict[str, Any]:
        """Extract metadata from Instagram URL without downloading.

        Returns:
            Dictionary with video/photo information
        """
        ydl_opts = {
            **self._get_ydl_opts(),
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
            **self._get_ydl_opts(),
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
                # Check file size
                file_size_mb = media_file.stat().st_size / (1024 * 1024)
                if file_size_mb > settings.max_file_size_mb:
                    media_file.unlink()  # Delete oversized file
                    raise DownloadFailedError(
                        f"File size ({file_size_mb:.1f}MB) exceeds limit ({settings.max_file_size_mb}MB)",
                        details={"file_size_mb": file_size_mb, "limit_mb": settings.max_file_size_mb}
                    )
                logger.info(f"Media file found: {media_file} ({file_size_mb:.1f}MB)")
                return media_file

        # If not found with expected naming, search directory
        media_files = list(target_dir.glob(f"*{shortcode}*"))
        if media_files:
            media_file = media_files[0]
            # Check file size
            file_size_mb = media_file.stat().st_size / (1024 * 1024)
            if file_size_mb > settings.max_file_size_mb:
                media_file.unlink()  # Delete oversized file
                raise DownloadFailedError(
                    f"File size ({file_size_mb:.1f}MB) exceeds limit ({settings.max_file_size_mb}MB)",
                    details={"file_size_mb": file_size_mb, "limit_mb": settings.max_file_size_mb}
                )
            logger.warning(f"Using alternative file: {media_file} ({file_size_mb:.1f}MB)")
            return media_file

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
