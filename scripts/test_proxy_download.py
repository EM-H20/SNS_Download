#!/usr/bin/env python3
"""Test Instagram proxy download without authentication.

This script tests various methods to download Instagram content
without requiring login credentials.

Usage:
    python scripts/test_proxy_download.py <shortcode>

Example:
    python scripts/test_proxy_download.py DPQelKMjMGG
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.instagram_proxy import InstagramProxyDownloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_proxy_download(shortcode: str) -> None:
    """Test proxy-based download without authentication.

    Args:
        shortcode: Instagram post shortcode
    """
    logger.info(f"🔍 Testing proxy download for: {shortcode}")
    logger.info("=" * 60)

    downloader = InstagramProxyDownloader()

    try:
        # Try to get media URLs
        logger.info("📥 Attempting to extract media URLs...")
        data = downloader.get_media_urls(shortcode)

        if not data:
            logger.error("❌ No data returned")
            return

        # Display results
        logger.info("✅ Extraction successful!")
        logger.info(f"📊 Method used: {data.get('method')}")
        logger.info("=" * 60)

        if data.get('method') == 'oembed':
            logger.info("📄 oEmbed Data:")
            logger.info(f"  - Author: {data.get('author')}")
            logger.info(f"  - Title: {data.get('title', '')[:100]}")
            logger.info(f"  - Thumbnail: {data.get('thumbnail_url', 'N/A')[:80]}")
            logger.info(f"  - Dimensions: {data.get('width')}x{data.get('height')}")

        elif data.get('method') == 'embed':
            logger.info("🌐 Embed Page Data:")
            logger.info(f"  - Media Type: {'Video' if data.get('is_video') else 'Photo'}")
            logger.info(f"  - Carousel: {'Yes' if data.get('is_carousel') else 'No'}")
            logger.info(f"  - URLs found: {len(data.get('media_urls', []))}")
            for i, url in enumerate(data.get('media_urls', [])[:3], 1):
                logger.info(f"    {i}. {url[:80]}...")

        elif data.get('method') == 'json':
            logger.info("📋 JSON Endpoint Data:")
            logger.info(f"  - Type: {'Video' if data.get('is_video') else 'Photo'}")
            logger.info(f"  - TypeName: {data.get('typename')}")
            if data.get('video_url'):
                logger.info(f"  - Video URL: {data.get('video_url')[:80]}...")
            if data.get('display_url'):
                logger.info(f"  - Display URL: {data.get('display_url')[:80]}...")

        logger.info("=" * 60)
        logger.info("✅ Test completed!")

        # Summary
        logger.info("")
        logger.info("📝 Summary:")
        if data.get('method') == 'oembed':
            logger.info("  ⚠️  oEmbed only provides thumbnails, not full videos")
            logger.info("  💡 This method works but is limited")
        elif data.get('method') == 'embed':
            logger.info("  ✅ Embed method found CDN URLs")
            logger.info("  💡 These URLs can be used for direct download")
        elif data.get('method') == 'json':
            logger.info("  ✅ JSON endpoint returned media URLs")
            logger.info("  🎉 Full quality video/photo URLs available")
        else:
            logger.info("  ⚠️  Unknown method")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        logger.exception("Full traceback:")
        logger.info("")
        logger.info("📝 Troubleshooting:")
        logger.info("  1. Instagram may have blocked this shortcode")
        logger.info("  2. The post might be from a private account")
        logger.info("  3. Instagram's API structure may have changed")
        logger.info("  4. Rate limiting may be in effect")
        logger.info("")
        logger.info("💡 Alternative: Use Instaloader with authentication")
        logger.info("   See INSTAGRAM_AUTHENTICATION_GUIDE.md")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_proxy_download.py <shortcode>")
        print("Example: python scripts/test_proxy_download.py DPQelKMjMGG")
        sys.exit(1)

    shortcode = sys.argv[1]
    test_proxy_download(shortcode)
