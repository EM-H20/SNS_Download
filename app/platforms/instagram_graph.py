"""Instagram Graph API platform for business/creator accounts.

Provides legal access to Instagram content from authenticated business accounts.
Supports:
- User's own posts, reels, stories
- Media metadata and insights
- OAuth 2.0 authentication flow
"""

import logging
import requests
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from app.config import settings
from app.models import MediaMetadata
from app.exceptions import (
    ContentNotFoundError,
    DownloadFailedError,
    AuthenticationError,
)
from .base import BasePlatform, PlatformType

logger = logging.getLogger(__name__)


class InstagramGraphPlatform(BasePlatform):
    """Instagram Graph API downloader for business accounts."""

    GRAPH_API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, access_token: Optional[str] = None):
        """Initialize Instagram Graph API platform.

        Args:
            access_token: Instagram Graph API access token (optional, uses settings if not provided)
        """
        self.access_token = access_token or settings.instagram_graph_api_token

    @property
    def platform_name(self) -> PlatformType:
        return PlatformType.INSTAGRAM

    def can_handle(self, url: str) -> bool:
        """Check if URL is from Instagram.

        Note: Graph API requires authentication, so this returns True for Instagram URLs
        only if access token is configured.
        """
        if not self.access_token:
            logger.warning("Instagram Graph API token not configured")
            return False

        return "instagram.com" in url

    def extract_identifier(self, url: str) -> str:
        """Extract media ID from Instagram URL.

        For Graph API, we need to convert the shortcode to media ID.
        This is a simplified version - production should use IG API lookup.

        Args:
            url: Instagram URL

        Returns:
            Media shortcode (will be converted to ID via API)

        Raises:
            ValueError: If URL format is invalid
        """
        import re

        # Extract shortcode from various Instagram URL formats
        patterns = [
            r'instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)',
            r'instagram\.com/[^/]+/(?:p|reel)/([A-Za-z0-9_-]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise ValueError(f"Invalid Instagram URL format: {url}")

    def get_media_info(self, media_id: str) -> Dict[str, Any]:
        """Get media information from Graph API.

        Args:
            media_id: Instagram media ID

        Returns:
            Media information dictionary

        Raises:
            AuthenticationError: If access token is invalid
            ContentNotFoundError: If media not found
            DownloadFailedError: If API request fails
        """
        if not self.access_token:
            raise AuthenticationError(
                "Instagram Graph API token not configured",
                details={"help": "Set INSTAGRAM_GRAPH_API_TOKEN in .env"}
            )

        url = f"{self.GRAPH_API_BASE}/{media_id}"
        params = {
            "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp,username",
            "access_token": self.access_token,
        }

        try:
            response = requests.get(url, params=params, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Invalid Instagram Graph API token",
                    details={"error": str(e)}
                )
            elif e.response.status_code == 404:
                raise ContentNotFoundError(
                    "Instagram media not found or not accessible",
                    details={"media_id": media_id}
                )
            else:
                raise DownloadFailedError(
                    f"Instagram Graph API request failed: {str(e)}",
                    details={"media_id": media_id, "status_code": e.response.status_code}
                )

        except requests.exceptions.RequestException as e:
            raise DownloadFailedError(
                f"Instagram Graph API request failed: {str(e)}",
                details={"media_id": media_id}
            )

    def download_media_file(self, media_url: str, output_path: Path) -> Path:
        """Download media file from URL.

        Args:
            media_url: Direct media URL from Graph API
            output_path: Where to save the file

        Returns:
            Path to downloaded file

        Raises:
            DownloadFailedError: If download fails
        """
        try:
            response = requests.get(
                media_url,
                stream=True,
                timeout=settings.request_timeout_seconds,
                headers={"User-Agent": settings.user_agent}
            )
            response.raise_for_status()

            # Write file in chunks
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded media to {output_path} ({output_path.stat().st_size:,} bytes)")
            return output_path

        except Exception as e:
            raise DownloadFailedError(
                f"Failed to download media file: {str(e)}",
                details={"media_url": media_url}
            )

    def download(
        self,
        url: str,
        output_dir: Optional[Path] = None
    ) -> Tuple[Path, Optional[Path], MediaMetadata]:
        """Download Instagram media using Graph API.

        Args:
            url: Instagram URL
            output_dir: Output directory (defaults to settings.download_dir)

        Returns:
            Tuple of (media_path, thumbnail_path, metadata)

        Raises:
            AuthenticationError: If token is invalid
            ContentNotFoundError: Media not found
            DownloadFailedError: Download failed
        """
        if output_dir is None:
            output_dir = settings.download_dir

        shortcode = self.extract_identifier(url)
        logger.info(f"Downloading Instagram media via Graph API: {shortcode}")

        # For now, we'll need to get the media ID from the shortcode
        # This requires either:
        # 1. Business discovery API (requires user's business account)
        # 2. User's own media endpoint
        # 3. Webhook/callback with media ID

        # Simplified: assume we have media ID (in production, implement proper lookup)
        # For MVP, we'll document this limitation
        raise NotImplementedError(
            "Instagram Graph API requires media ID, not shortcode. "
            "Please use the /me/media endpoint to list your own media, "
            "or implement Business Discovery API for other accounts."
        )

    def list_user_media(self, user_id: str = "me", limit: int = 25) -> Dict[str, Any]:
        """List media from authenticated user's account.

        Args:
            user_id: Instagram user ID (default "me" for authenticated user)
            limit: Number of media items to retrieve

        Returns:
            Dictionary with media data

        Raises:
            AuthenticationError: If token is invalid
            DownloadFailedError: If API request fails
        """
        if not self.access_token:
            raise AuthenticationError(
                "Instagram Graph API token not configured",
                details={"help": "Set INSTAGRAM_GRAPH_API_TOKEN in .env"}
            )

        url = f"{self.GRAPH_API_BASE}/{user_id}/media"
        params = {
            "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp",
            "limit": limit,
            "access_token": self.access_token,
        }

        try:
            response = requests.get(url, params=params, timeout=settings.request_timeout_seconds)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                raise AuthenticationError(
                    "Invalid Instagram Graph API token",
                    details={"error": str(e)}
                )
            else:
                raise DownloadFailedError(
                    f"Instagram Graph API request failed: {str(e)}",
                    details={"user_id": user_id, "status_code": e.response.status_code}
                )

        except requests.exceptions.RequestException as e:
            raise DownloadFailedError(
                f"Instagram Graph API request failed: {str(e)}",
                details={"user_id": user_id}
            )

    def get_platform_info(self) -> dict:
        """Get Instagram Graph API platform information."""
        return {
            "platform": self.platform_name.value,
            "api_type": "Instagram Graph API",
            "supported_types": ["video", "photo", "carousel"],
            "requires_auth": True,
            "auth_configured": bool(self.access_token),
            "auth_type": "OAuth 2.0 with Facebook Login",
            "limitations": [
                "Only own business/creator account content",
                "Requires app review for production",
                "Rate limits apply (200 calls/hour per user)"
            ],
            "notes": "Legal access to Instagram content via official Meta API"
        }
