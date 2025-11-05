"""Instagram GraphQL API client for downloading public media.

Uses Instagram's public GraphQL API to fetch media URLs without authentication.
Supports videos, photos, and carousel posts.
"""

import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.config import settings
from app.exceptions import (
    PrivateAccountError,
    ContentNotFoundError,
    RateLimitExceededError,
    InstagramAPIError,
)

logger = logging.getLogger(__name__)


class InstagramGraphQL:
    """Instagram GraphQL API client for public posts."""

    # Instagram's public GraphQL endpoint
    GRAPHQL_URL = "https://www.instagram.com/graphql/query/"

    # Web interface endpoint (fallback)
    WEB_URL = "https://www.instagram.com/p/{shortcode}/?__a=1&__d=dis"

    def __init__(self):
        """Initialize GraphQL client with browser-like headers."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.user_agent,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com',
        })

    def get_post_data(self, shortcode: str) -> Dict[str, Any]:
        """Fetch post data from Instagram's public API.

        Args:
            shortcode: Instagram post shortcode (8-15 characters)

        Returns:
            Dictionary containing post metadata and media URLs

        Raises:
            ContentNotFoundError: Post doesn't exist or was deleted
            PrivateAccountError: Post is from a private account
            RateLimitExceededError: Instagram rate limiting detected
            InstagramAPIError: API structure changed or other errors
        """
        try:
            logger.info(f"Fetching post data for shortcode: {shortcode}")

            # Fetch HTML page and extract JSON from script tag
            url = f"https://www.instagram.com/p/{shortcode}/"
            response = self.session.get(
                url,
                timeout=settings.request_timeout_seconds
            )

            # Check for rate limiting
            if response.status_code == 429:
                logger.warning(f"Rate limit hit for {shortcode}")
                raise RateLimitExceededError(
                    "Instagram rate limit exceeded, please try again later",
                    details={"shortcode": shortcode, "retry_after_seconds": 300}
                )

            # Check for not found
            if response.status_code == 404:
                logger.warning(f"Post not found: {shortcode}")
                raise ContentNotFoundError(
                    "Post does not exist or has been deleted",
                    details={"shortcode": shortcode}
                )

            # Check if redirected to login page
            if 'login' in response.url.lower():
                logger.warning(f"Redirected to login for {shortcode}")
                raise PrivateAccountError(
                    "Instagram requires login to view this content",
                    details={"shortcode": shortcode}
                )

            response.raise_for_status()

            # Extract JSON data from HTML
            post_data = self._extract_json_from_html(response.text, shortcode)

            # Check if private
            if post_data.get('is_private', False):
                logger.warning(f"Private post: {shortcode}")
                raise PrivateAccountError(
                    "This post is from a private account",
                    details={"shortcode": shortcode}
                )

            logger.info(f"Successfully fetched data for {shortcode}")
            return self._parse_post_data(post_data, shortcode)

        except (PrivateAccountError, ContentNotFoundError, RateLimitExceededError, InstagramAPIError):
            raise
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {shortcode}")
            raise InstagramAPIError(
                "Request timed out while fetching post data",
                details={"shortcode": shortcode}
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {shortcode}: {str(e)}")
            raise InstagramAPIError(
                f"Failed to fetch post data: {str(e)}",
                details={"shortcode": shortcode}
            )

    def _extract_json_from_html(self, html: str, shortcode: str) -> Dict[str, Any]:
        """Extract JSON data from Instagram HTML page.

        Args:
            html: HTML content
            shortcode: Post shortcode

        Returns:
            Post data dictionary

        Raises:
            InstagramAPIError: Failed to extract JSON data
        """
        import json
        import re

        # Look for JSON data in script tags
        # Instagram embeds data in <script type="application/ld+json">
        patterns = [
            r'<script type="application/ld\+json">({.*?})</script>',
            r'window\._sharedData = ({.*?});</script>',
            r'"xdt_api__v1__media__shortcode__web_info":\s*({.*?})(?:,|\})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            if matches:
                try:
                    data = json.loads(matches[0])
                    logger.debug(f"Extracted JSON data using pattern: {pattern[:50]}")

                    # Try different data structures
                    if '@type' in data and data['@type'] == 'ImageObject':
                        return self._parse_ld_json(data, shortcode)
                    elif 'entry_data' in data:
                        return self._parse_shared_data(data, shortcode)
                    elif 'items' in data:
                        return data['items'][0] if data['items'] else {}

                except json.JSONDecodeError:
                    continue

        # If no JSON found, this might be login-required
        logger.error(f"Failed to extract JSON data for {shortcode}")
        raise InstagramAPIError(
            "Could not extract post data from Instagram page",
            details={"shortcode": shortcode}
        )

    def _parse_ld_json(self, data: Dict[str, Any], shortcode: str) -> Dict[str, Any]:
        """Parse JSON-LD structured data format.

        Args:
            data: JSON-LD data
            shortcode: Post shortcode

        Returns:
            Standardized post data
        """
        return {
            '__typename': 'GraphImage',
            'shortcode': shortcode,
            'is_video': data.get('@type') == 'VideoObject',
            'display_url': data.get('contentUrl') or data.get('url'),
            'video_url': data.get('contentUrl') if data.get('@type') == 'VideoObject' else None,
            'edge_media_to_caption': {
                'edges': [{'node': {'text': data.get('caption', '')}}]
            },
            'owner': {
                'username': data.get('author', {}).get('identifier', '') if isinstance(data.get('author'), dict) else '',
            },
            'edge_media_preview_like': {'count': data.get('interactionStatistic', {}).get('userInteractionCount', 0)},
            'edge_media_to_comment': {'count': data.get('commentCount', 0)},
        }

    def _parse_shared_data(self, data: Dict[str, Any], shortcode: str) -> Dict[str, Any]:
        """Parse window._sharedData format.

        Args:
            data: Shared data object
            shortcode: Post shortcode

        Returns:
            Post data from shared data
        """
        try:
            post_page = data['entry_data']['PostPage'][0]
            media = post_page['graphql']['shortcode_media']
            return media
        except (KeyError, IndexError) as e:
            logger.error(f"Failed to parse shared data: {e}")
            raise InstagramAPIError(
                "Failed to parse Instagram data structure",
                details={"shortcode": shortcode}
            )

    def _parse_post_data(self, data: Dict[str, Any], shortcode: str) -> Dict[str, Any]:
        """Parse Instagram API response into standardized format.

        Args:
            data: Raw API response data
            shortcode: Post shortcode

        Returns:
            Standardized post data dictionary
        """
        # Determine media type
        typename = data.get('__typename', '')
        is_video = data.get('is_video', False)

        # Extract carousel items if present
        carousel_items = []
        if typename == 'GraphSidecar' or 'edge_sidecar_to_children' in data:
            edges = data.get('edge_sidecar_to_children', {}).get('edges', [])
            for edge in edges:
                node = edge.get('node', {})
                carousel_items.append({
                    'is_video': node.get('is_video', False),
                    'url': node.get('video_url') if node.get('is_video') else node.get('display_url'),
                    'width': node.get('dimensions', {}).get('width'),
                    'height': node.get('dimensions', {}).get('height'),
                })

        # Get caption
        caption_edges = data.get('edge_media_to_caption', {}).get('edges', [])
        caption = caption_edges[0]['node']['text'] if caption_edges else ""

        # Get owner info
        owner = data.get('owner', {})

        # Build standardized response
        parsed = {
            'shortcode': shortcode,
            'typename': typename,
            'is_video': is_video,
            'is_carousel': len(carousel_items) > 0,
            'caption': caption,
            'timestamp': data.get('taken_at_timestamp', int(datetime.now().timestamp())),

            # Media URLs
            'video_url': data.get('video_url'),
            'display_url': data.get('display_url'),
            'thumbnail_url': data.get('thumbnail_src') or data.get('display_url'),

            # Carousel items
            'carousel_items': carousel_items,

            # Dimensions
            'width': data.get('dimensions', {}).get('width'),
            'height': data.get('dimensions', {}).get('height'),

            # Engagement
            'likes': data.get('edge_media_preview_like', {}).get('count', 0),
            'comments': data.get('edge_media_to_comment', {}).get('count', 0),
            'views': data.get('video_view_count', 0) if is_video else None,

            # Author
            'author': {
                'username': owner.get('username', ''),
                'full_name': owner.get('full_name', ''),
                'profile_pic_url': owner.get('profile_pic_url', ''),
                'is_verified': owner.get('is_verified', False),
            },

            # Location
            'location': data.get('location', {}).get('name') if data.get('location') else None,
        }

        return parsed

    def download_media(self, url: str, output_path: str) -> None:
        """Download media file from URL.

        Args:
            url: Media URL (from Instagram CDN)
            output_path: Local file path to save media
        """
        logger.info(f"Downloading media from {url}")

        response = self.session.get(url, stream=True, timeout=30)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info(f"Media saved to {output_path}")
