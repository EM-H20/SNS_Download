#!/usr/bin/env python3
"""Test script for Instagram downloads using Instaloader.

This script demonstrates how to download Instagram content with authentication.
It requires Instagram credentials to be set in .env file.

Usage:
    python scripts/test_instaloader.py <shortcode>

Example:
    python scripts/test_instaloader.py DPQelKMjMGG
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
import instaloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_instaloader_download(shortcode: str) -> None:
    """Test Instaloader download with authentication.

    Args:
        shortcode: Instagram post shortcode (e.g., DPQelKMjMGG)
    """
    logger.info(f"Testing Instaloader download for: {shortcode}")

    # Check for credentials
    if not settings.instagram_username or not settings.instagram_password:
        logger.error("❌ Instagram credentials not found in .env")
        logger.error("Please add INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to .env file")
        logger.error("See INSTAGRAM_AUTHENTICATION_GUIDE.md for setup instructions")
        return

    logger.info(f"✅ Credentials found for: {settings.instagram_username}")

    # Initialize Instaloader
    L = instaloader.Instaloader(
        download_videos=True,
        download_video_thumbnails=True,
        download_comments=settings.include_comments,
        save_metadata=settings.save_metadata,
        compress_json=False,  # Pretty print JSON
        dirname_pattern=str(settings.download_dir / "{target}"),
    )

    try:
        # Login
        logger.info("🔐 Attempting login...")
        L.login(settings.instagram_username, settings.instagram_password)
        logger.info("✅ Login successful!")

        # Get post
        logger.info(f"📥 Fetching post: {shortcode}")
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Display post info
        logger.info(f"📊 Post Information:")
        logger.info(f"  - Type: {'Video' if post.is_video else 'Photo'}")
        logger.info(f"  - Carousel: {'Yes' if hasattr(post, 'get_sidecar_nodes') and list(post.get_sidecar_nodes()) else 'No'}")
        logger.info(f"  - Owner: @{post.owner_username}")
        logger.info(f"  - Likes: {post.likes}")
        logger.info(f"  - Comments: {post.comments}")
        logger.info(f"  - Caption: {post.caption[:100]}..." if post.caption else "  - Caption: None")

        # Download
        logger.info(f"⬇️  Downloading...")
        L.download_post(post, target=shortcode)

        logger.info(f"✅ Download completed successfully!")
        logger.info(f"📁 Files saved to: {settings.download_dir / shortcode}")

        # List downloaded files
        download_path = settings.download_dir / shortcode
        if download_path.exists():
            files = list(download_path.iterdir())
            logger.info(f"📄 Downloaded {len(files)} file(s):")
            for f in files:
                logger.info(f"  - {f.name} ({f.stat().st_size:,} bytes)")

    except instaloader.exceptions.BadCredentialsException:
        logger.error("❌ Login failed: Invalid username or password")
        logger.error("Please check your credentials in .env file")

    except instaloader.exceptions.TwoFactorAuthRequiredException:
        logger.error("❌ Two-factor authentication required")
        logger.error("Please disable 2FA for your test account or use session file")

    except instaloader.exceptions.ConnectionException as e:
        logger.error(f"❌ Connection error: {e}")
        logger.error("Instagram may be blocking requests or rate limiting")

    except Exception as e:
        logger.exception(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/test_instaloader.py <shortcode>")
        print("Example: python scripts/test_instaloader.py DPQelKMjMGG")
        sys.exit(1)

    shortcode = sys.argv[1]
    test_instaloader_download(shortcode)
