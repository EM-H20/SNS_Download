"""URL parsing and validation for Instagram Reels.

Handles multiple URL formats and extracts shortcodes for API consumption.
"""

import re
from typing import Optional
from urllib.parse import urlparse

from app.exceptions import InvalidURLError


class ReelsURLParser:
    """Parser for Instagram Reels URLs with support for multiple formats."""

    # Instagram uses shortcodes for both /reel/ and /p/ paths
    # Pattern: alphanumeric + underscore + hyphen, typically 11 characters
    SHORTCODE_PATTERN = re.compile(r'^[A-Za-z0-9_-]{11}$')

    # Supported URL patterns for Reels content
    URL_PATTERNS = [
        re.compile(r'instagram\.com/reel/([A-Za-z0-9_-]+)'),
        re.compile(r'instagram\.com/p/([A-Za-z0-9_-]+)'),  # Posts can also be videos
        re.compile(r'instagram\.com/tv/([A-Za-z0-9_-]+)'),  # Legacy IGTV format
        re.compile(r'instagram\.com/[^/]+/reel/([A-Za-z0-9_-]+)'),  # Username/reel format
    ]

    @classmethod
    def extract_shortcode(cls, url: str) -> str:
        """Extract Instagram shortcode from various URL formats.

        Args:
            url: Instagram URL in any supported format

        Returns:
            11-character shortcode used by Instagram API

        Raises:
            InvalidURLError: If URL format is invalid or shortcode cannot be extracted

        Examples:
            >>> ReelsURLParser.extract_shortcode("https://instagram.com/reel/ABC_123-xyz/")
            "ABC_123-xyz"
        """
        if not url or not isinstance(url, str):
            raise InvalidURLError("URL must be a non-empty string")

        # Normalize URL - remove query parameters and fragments
        parsed = urlparse(url)
        clean_url = f"{parsed.netloc}{parsed.path}"

        # Try each pattern to extract shortcode
        for pattern in cls.URL_PATTERNS:
            match = pattern.search(clean_url)
            if match:
                shortcode = match.group(1)
                # Validate shortcode format
                if cls.SHORTCODE_PATTERN.match(shortcode):
                    return shortcode
                else:
                    raise InvalidURLError(
                        f"Invalid shortcode format: {shortcode}",
                        details={"shortcode": shortcode, "url": url}
                    )

        raise InvalidURLError(
            "URL does not match any supported Instagram format",
            details={
                "url": url,
                "supported_formats": ["/reel/", "/p/", "/tv/"]
            }
        )

    @classmethod
    def validate_url(cls, url: str) -> bool:
        """Check if URL is a valid Instagram Reels URL.

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            cls.extract_shortcode(url)
            return True
        except InvalidURLError:
            return False

    @classmethod
    def normalize_url(cls, url: str) -> str:
        """Convert any Instagram URL to canonical format.

        Args:
            url: Instagram URL in any format

        Returns:
            Canonical URL: https://www.instagram.com/reel/{shortcode}/
        """
        shortcode = cls.extract_shortcode(url)
        return f"https://www.instagram.com/reel/{shortcode}/"
