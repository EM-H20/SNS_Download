"""Instagram media download using proxy/embed method (SaveFrom.net style).

This approach attempts to extract media URLs from Instagram's embed endpoints
and CDN direct links without authentication.

WARNING: This is a workaround and may be blocked by Instagram at any time.
Use with caution and respect rate limits.
"""

import logging
import re
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.config import settings
from app.exceptions import (
    ContentNotFoundError,
    DownloadFailedError,
    InstagramAPIError,
)

logger = logging.getLogger(__name__)


class InstagramProxyDownloader:
    """Instagram downloader using embed and oembed endpoints."""

    # Instagram's oEmbed API (public, no auth required)
    OEMBED_URL = "https://graph.facebook.com/v12.0/instagram_oembed"

    # Instagram embed endpoint
    EMBED_URL = "https://www.instagram.com/p/{shortcode}/embed/"

    # Alternative: Direct CDN pattern matching
    CDN_PATTERNS = [
        r'https://.*\.cdninstagram\.com/.*\.(jpg|png|mp4)',
        r'https://scontent.*\.cdninstagram\.com/.*\.(jpg|png|mp4)',
        r'https://.*\.fbcdn\.net/.*\.(jpg|png|mp4)',
    ]

    def __init__(self):
        """Initialize with browser-like headers."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com',
        })

    def get_media_urls(self, shortcode: str) -> Dict[str, Any]:
        """Extract media URLs without authentication.

        Tries multiple methods:
        1. oEmbed API (official, public)
        2. Embed page parsing
        3. CDN URL extraction

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Dictionary with media URLs and metadata

        Raises:
            ContentNotFoundError: Post not found
            InstagramAPIError: Extraction failed
        """
        logger.info(f"Attempting proxy download for: {shortcode}")

        # Method 1: Try oEmbed API
        try:
            oembed_data = self._try_oembed(shortcode)
            if oembed_data:
                return oembed_data
        except Exception as e:
            logger.warning(f"oEmbed failed: {e}")

        # Method 2: Try embed page
        try:
            embed_data = self._try_embed_page(shortcode)
            if embed_data:
                return embed_data
        except Exception as e:
            logger.warning(f"Embed page failed: {e}")

        # Method 3: Try public JSON endpoint
        try:
            json_data = self._try_json_endpoint(shortcode)
            if json_data:
                return json_data
        except Exception as e:
            logger.warning(f"JSON endpoint failed: {e}")

        raise InstagramAPIError(
            "All proxy methods failed - Instagram may require authentication",
            details={"shortcode": shortcode}
        )

    def _try_oembed(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Try Instagram oEmbed API (public endpoint).

        Args:
            shortcode: Post shortcode

        Returns:
            Media data if successful, None otherwise
        """
        url = f"https://www.instagram.com/p/{shortcode}/"

        try:
            response = self.session.get(
                self.OEMBED_URL,
                params={
                    'url': url,
                    'maxwidth': 640,
                },
                timeout=10
            )

            if response.status_code == 404:
                raise ContentNotFoundError(
                    "Post not found",
                    details={"shortcode": shortcode}
                )

            response.raise_for_status()
            data = response.json()

            logger.info(f"oEmbed success for {shortcode}")

            # Extract thumbnail URL from HTML
            thumbnail_url = None
            if 'thumbnail_url' in data:
                thumbnail_url = data['thumbnail_url']

            return {
                'method': 'oembed',
                'shortcode': shortcode,
                'thumbnail_url': thumbnail_url,
                'author': data.get('author_name'),
                'author_url': data.get('author_url'),
                'title': data.get('title'),
                'html': data.get('html'),
                'width': data.get('thumbnail_width'),
                'height': data.get('thumbnail_height'),
            }

        except requests.exceptions.RequestException as e:
            logger.warning(f"oEmbed request failed: {e}")
            return None

    def _try_embed_page(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Try to extract media from embed page.

        Args:
            shortcode: Post shortcode

        Returns:
            Media data if successful, None otherwise
        """
        embed_url = self.EMBED_URL.format(shortcode=shortcode)

        try:
            response = self.session.get(
                embed_url,
                timeout=10,
                allow_redirects=True
            )

            if response.status_code == 404:
                raise ContentNotFoundError(
                    "Post not found",
                    details={"shortcode": shortcode}
                )

            response.raise_for_status()
            html = response.text

            # Extract media URLs using regex
            media_urls = self._extract_cdn_urls(html)

            if not media_urls:
                logger.warning("No CDN URLs found in embed page")
                return None

            logger.info(f"Embed page success for {shortcode}: {len(media_urls)} URLs")

            # Determine media type
            has_video = any('.mp4' in url for url in media_urls)
            has_image = any(url.endswith(('.jpg', '.png')) for url in media_urls)

            return {
                'method': 'embed',
                'shortcode': shortcode,
                'media_urls': media_urls,
                'is_video': has_video,
                'is_photo': has_image and not has_video,
                'is_carousel': len(media_urls) > 2,  # Heuristic
            }

        except requests.exceptions.RequestException as e:
            logger.warning(f"Embed page request failed: {e}")
            return None

    def _try_json_endpoint(self, shortcode: str) -> Optional[Dict[str, Any]]:
        """Try to get data from Instagram's __a=1 endpoint.

        Args:
            shortcode: Post shortcode

        Returns:
            Media data if successful, None otherwise
        """
        url = f"https://www.instagram.com/p/{shortcode}/"

        try:
            response = self.session.get(
                url,
                params={'__a': '1', '__d': 'dis'},
                timeout=10
            )

            if response.status_code == 404:
                raise ContentNotFoundError(
                    "Post not found",
                    details={"shortcode": shortcode}
                )

            # Check if redirected to login
            if 'login' in response.url.lower():
                logger.warning("Redirected to login page")
                return None

            response.raise_for_status()

            # Try to parse JSON
            try:
                data = response.json()

                # Navigate to media data
                if 'graphql' in data:
                    media = data['graphql']['shortcode_media']
                elif 'items' in data:
                    media = data['items'][0]
                else:
                    return None

                logger.info(f"JSON endpoint success for {shortcode}")

                # Extract URLs
                video_url = media.get('video_url')
                display_url = media.get('display_url')

                return {
                    'method': 'json',
                    'shortcode': shortcode,
                    'video_url': video_url,
                    'display_url': display_url,
                    'is_video': media.get('is_video', False),
                    'typename': media.get('__typename'),
                }

            except ValueError:
                logger.warning("Response is not valid JSON")
                return None

        except requests.exceptions.RequestException as e:
            logger.warning(f"JSON endpoint request failed: {e}")
            return None

    def _extract_cdn_urls(self, html: str) -> List[str]:
        """Extract CDN URLs from HTML using regex patterns.

        Args:
            html: HTML content

        Returns:
            List of CDN URLs
        """
        urls = []

        # Simple patterns that capture full URLs
        simple_patterns = [
            r'https://[^\s"\'<>]+\.cdninstagram\.com/[^\s"\'<>]+\.(?:jpg|png|mp4)',
            r'https://scontent[^\s"\'<>]+\.cdninstagram\.com/[^\s"\'<>]+\.(?:jpg|png|mp4)',
            r'https://[^\s"\'<>]+\.fbcdn\.net/[^\s"\'<>]+\.(?:jpg|png|mp4)',
        ]

        for pattern in simple_patterns:
            matches = re.findall(pattern, html)
            urls.extend(matches)

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for url in urls:
            if url not in seen and url.startswith('http'):
                seen.add(url)
                result.append(url)

        return result

    def download_media(self, url: str, output_path: str) -> None:
        """Download media from CDN URL.

        Args:
            url: CDN URL
            output_path: Local file path
        """
        logger.info(f"Downloading from CDN: {url}")

        response = self.session.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Download complete: {output_path}")
