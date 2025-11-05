"""Metadata storage system for Instagram post text data.

Handles saving, loading, and managing JSON metadata files with UTF-8 encoding
for Korean and other non-ASCII text support.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

from app.config import settings
from app.exceptions import DownloadFailedError

logger = logging.getLogger(__name__)


class MetadataStorage:
    """Storage manager for Instagram post metadata."""

    @staticmethod
    def get_metadata_path(shortcode: str) -> Path:
        """Get the file path for metadata JSON.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Path to metadata JSON file
        """
        return settings.download_dir / shortcode / f"{shortcode}_metadata.json"

    @classmethod
    def save_metadata(cls, shortcode: str, metadata: Dict[str, Any]) -> Path:
        """Save metadata to JSON file with UTF-8 encoding.

        Args:
            shortcode: Instagram post shortcode
            metadata: Metadata dictionary to save

        Returns:
            Path to saved JSON file

        Raises:
            DownloadFailedError: If save fails
        """
        try:
            metadata_path = cls.get_metadata_path(shortcode)

            # Ensure directory exists
            metadata_path.parent.mkdir(parents=True, exist_ok=True)

            # Save with UTF-8 encoding and pretty print
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(
                    metadata,
                    f,
                    ensure_ascii=False,  # Allow Korean and other non-ASCII
                    indent=2,
                    sort_keys=False
                )

            logger.info(f"Metadata saved: {metadata_path} ({metadata_path.stat().st_size} bytes)")
            return metadata_path

        except Exception as e:
            logger.error(f"Failed to save metadata for {shortcode}: {e}")
            raise DownloadFailedError(
                f"Failed to save metadata: {str(e)}",
                details={"shortcode": shortcode}
            )

    @classmethod
    def load_metadata(cls, shortcode: str) -> Optional[Dict[str, Any]]:
        """Load metadata from JSON file.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Metadata dictionary or None if not found
        """
        try:
            metadata_path = cls.get_metadata_path(shortcode)

            if not metadata_path.exists():
                logger.debug(f"Metadata not found: {metadata_path}")
                return None

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            logger.info(f"Metadata loaded: {metadata_path}")
            return metadata

        except Exception as e:
            logger.warning(f"Failed to load metadata for {shortcode}: {e}")
            return None

    @classmethod
    def update_metadata(cls, shortcode: str, updates: Dict[str, Any]) -> Optional[Path]:
        """Update existing metadata with new fields.

        Args:
            shortcode: Instagram post shortcode
            updates: Dictionary of updates to apply

        Returns:
            Path to updated file or None if not found
        """
        try:
            # Load existing metadata
            metadata = cls.load_metadata(shortcode)

            if metadata is None:
                logger.warning(f"Cannot update - metadata not found for {shortcode}")
                return None

            # Deep merge updates
            metadata.update(updates)

            # Save updated metadata
            return cls.save_metadata(shortcode, metadata)

        except Exception as e:
            logger.error(f"Failed to update metadata for {shortcode}: {e}")
            return None

    @classmethod
    def metadata_exists(cls, shortcode: str) -> bool:
        """Check if metadata file exists.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            True if metadata file exists
        """
        return cls.get_metadata_path(shortcode).exists()

    @classmethod
    def delete_metadata(cls, shortcode: str) -> bool:
        """Delete metadata file.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            True if deleted successfully
        """
        try:
            metadata_path = cls.get_metadata_path(shortcode)

            if metadata_path.exists():
                metadata_path.unlink()
                logger.info(f"Metadata deleted: {metadata_path}")
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to delete metadata for {shortcode}: {e}")
            return False

    @classmethod
    def get_metadata_summary(cls, shortcode: str) -> Optional[Dict[str, Any]]:
        """Get quick summary of metadata without loading full file.

        Args:
            shortcode: Instagram post shortcode

        Returns:
            Summary dictionary with key fields
        """
        metadata = cls.load_metadata(shortcode)

        if metadata is None:
            return None

        # Extract key fields for quick access
        return {
            "shortcode": shortcode,
            "caption": metadata.get("post", {}).get("caption", ""),
            "hashtags": metadata.get("post", {}).get("hashtags", []),
            "mentions": metadata.get("post", {}).get("mentions", []),
            "likes": metadata.get("engagement", {}).get("likes", 0),
            "comments_count": metadata.get("engagement", {}).get("comments_count", 0),
            "author": metadata.get("author", {}).get("username", ""),
            "collected_at": metadata.get("collected_at"),
        }
