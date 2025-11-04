"""Custom exception hierarchy for domain-specific error handling.

Provides clear separation between different failure modes for proper
error recovery and user feedback.
"""

from typing import Optional


class ReelsDownloaderError(Exception):
    """Base exception for all downloader-related errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidURLError(ReelsDownloaderError):
    """Raised when URL format is invalid or not an Instagram Reels URL."""
    pass


class PrivateAccountError(ReelsDownloaderError):
    """Raised when attempting to download from a private account.

    This is expected behavior - we can only download from public accounts.
    """
    pass


class ContentNotFoundError(ReelsDownloaderError):
    """Raised when the Reels content doesn't exist or has been deleted."""
    pass


class RateLimitExceededError(ReelsDownloaderError):
    """Raised when Instagram rate limiting is detected.

    Client should implement exponential backoff and retry logic.
    """
    pass


class DownloadFailedError(ReelsDownloaderError):
    """Raised when media download fails after all retry attempts."""
    pass


class InstagramAPIError(ReelsDownloaderError):
    """Raised when Instagram's internal API structure has changed.

    This requires code updates to adapt to new Instagram API structure.
    """
    pass
