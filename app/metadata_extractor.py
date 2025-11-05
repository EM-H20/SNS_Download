"""Instagram metadata extraction for text data (captions, comments, hashtags).

Extracts rich metadata from Instagram posts including:
- Captions and descriptions
- Hashtags and mentions
- Engagement metrics (likes, comments, views)
- Author information
- Comments (optional, requires authentication)
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class InstagramMetadataExtractor:
    """Extract comprehensive metadata from Instagram posts."""

    @staticmethod
    def parse_hashtags(text: str) -> List[str]:
        """Extract hashtags from text.

        Args:
            text: Text containing hashtags

        Returns:
            List of hashtags without # symbol
        """
        if not text:
            return []

        # Find all hashtags (Korean and English supported)
        hashtags = re.findall(r'#([a-zA-Z0-9가-힣_]+)', text)
        return list(set(hashtags))  # Remove duplicates

    @staticmethod
    def parse_mentions(text: str) -> List[str]:
        """Extract @mentions from text.

        Args:
            text: Text containing mentions

        Returns:
            List of usernames without @ symbol
        """
        if not text:
            return []

        # Find all mentions
        mentions = re.findall(r'@([a-zA-Z0-9._]+)', text)
        return list(set(mentions))  # Remove duplicates

    @classmethod
    def extract_from_ytdlp(cls, info: Dict[str, Any], shortcode: str) -> Dict[str, Any]:
        """Extract metadata from yt-dlp info dictionary.

        Args:
            info: yt-dlp info dictionary
            shortcode: Instagram post shortcode

        Returns:
            Structured metadata dictionary
        """
        logger.info(f"Extracting metadata from yt-dlp for {shortcode}")

        # Get description/caption
        description = info.get('description', '') or ''
        title = info.get('title', '') or ''

        # Combine title and description for full caption
        caption = f"{title}\n{description}".strip() if title != description else description

        # Parse hashtags and mentions
        hashtags = cls.parse_hashtags(caption)
        mentions = cls.parse_mentions(caption)

        # Get engagement metrics
        likes = info.get('like_count', 0) or 0
        comments_count = info.get('comment_count', 0) or 0
        views = info.get('view_count', 0) or 0

        # Get author info
        uploader = info.get('uploader', '') or ''
        uploader_id = info.get('uploader_id', '') or ''
        uploader_url = info.get('uploader_url', '') or ''

        # Get timestamp
        timestamp = info.get('timestamp')
        created_at = datetime.fromtimestamp(timestamp).isoformat() if timestamp else None

        # Build metadata structure
        metadata = {
            "version": "1.0",
            "source": "yt-dlp",
            "shortcode": shortcode,
            "collected_at": datetime.utcnow().isoformat(),

            "post": {
                "type": "video" if info.get('vcodec') != 'none' else "photo",
                "url": f"https://instagram.com/p/{shortcode}/",
                "caption": caption,
                "hashtags": hashtags,
                "mentions": mentions,
                "created_at": created_at,
            },

            "engagement": {
                "likes": likes,
                "comments_count": comments_count,
                "views": views,
            },

            "author": {
                "username": uploader_id or uploader,
                "display_name": uploader,
                "profile_url": uploader_url,
            },

            "comments": [],  # yt-dlp doesn't provide detailed comments

            "raw_info": {
                "duration": info.get('duration'),
                "width": info.get('width'),
                "height": info.get('height'),
                "format": info.get('format'),
            }
        }

        logger.info(f"Extracted metadata: {len(hashtags)} hashtags, {len(mentions)} mentions")
        return metadata

    @classmethod
    def extract_from_instaloader(cls, post: Any, shortcode: str, include_comments: bool = False, max_comments: int = 50) -> Dict[str, Any]:
        """Extract metadata from Instaloader Post object.

        Args:
            post: Instaloader Post object
            shortcode: Instagram post shortcode
            include_comments: Whether to fetch comments (requires auth)
            max_comments: Maximum number of comments to fetch

        Returns:
            Structured metadata dictionary
        """
        logger.info(f"Extracting metadata from Instaloader for {shortcode}")

        try:
            # Get caption
            caption = post.caption or ''

            # Parse hashtags and mentions
            hashtags = cls.parse_hashtags(caption)
            mentions = cls.parse_mentions(caption)

            # Get engagement metrics
            likes = post.likes
            comments_count = post.comments
            views = post.video_view_count if post.is_video else 0

            # Get author info
            owner = post.owner_username
            owner_id = post.owner_id
            is_verified = getattr(post, 'owner_profile', {}).get('is_verified', False) if hasattr(post, 'owner_profile') else False

            # Get timestamp
            created_at = post.date_utc.isoformat() if post.date_utc else None

            # Get location
            location_name = post.location.name if post.location else None

            # Determine post type
            if post.typename == 'GraphSidecar':
                post_type = "carousel"
            elif post.is_video:
                post_type = "video"
            else:
                post_type = "photo"

            # Build metadata structure
            metadata = {
                "version": "1.0",
                "source": "instaloader",
                "shortcode": shortcode,
                "collected_at": datetime.utcnow().isoformat(),

                "post": {
                    "type": post_type,
                    "url": f"https://instagram.com/p/{shortcode}/",
                    "caption": caption,
                    "hashtags": hashtags,
                    "mentions": mentions,
                    "location": {
                        "name": location_name,
                    } if location_name else None,
                    "created_at": created_at,
                    "is_video": post.is_video,
                    "media_count": post.mediacount if hasattr(post, 'mediacount') else 1,
                },

                "engagement": {
                    "likes": likes,
                    "comments_count": comments_count,
                    "views": views,
                },

                "author": {
                    "username": owner,
                    "user_id": owner_id,
                    "is_verified": is_verified,
                    "profile_url": f"https://instagram.com/{owner}/",
                },

                "comments": [],

                "raw_info": {
                    "duration": post.video_duration if post.is_video else None,
                    "typename": post.typename,
                }
            }

            # Fetch comments if requested
            if include_comments:
                logger.info(f"Fetching up to {max_comments} comments for {shortcode}")
                try:
                    comments_list = []
                    for idx, comment in enumerate(post.get_comments()):
                        if idx >= max_comments:
                            break

                        comment_data = {
                            "id": comment.id,
                            "username": comment.owner.username,
                            "text": comment.text,
                            "likes": comment.likes_count,
                            "created_at": comment.created_at_utc.isoformat() if comment.created_at_utc else None,
                        }
                        comments_list.append(comment_data)

                    metadata["comments"] = comments_list
                    logger.info(f"Fetched {len(comments_list)} comments")

                except Exception as e:
                    logger.warning(f"Failed to fetch comments: {e}")
                    metadata["comments"] = []

            logger.info(f"Extracted metadata: {len(hashtags)} hashtags, {len(mentions)} mentions, {len(metadata['comments'])} comments")
            return metadata

        except Exception as e:
            logger.error(f"Error extracting Instaloader metadata: {e}")
            # Return minimal metadata on error
            return {
                "version": "1.0",
                "source": "instaloader",
                "shortcode": shortcode,
                "collected_at": datetime.utcnow().isoformat(),
                "error": str(e),
                "post": {},
                "engagement": {},
                "author": {},
                "comments": [],
            }
