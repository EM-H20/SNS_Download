"""Pydantic models for request/response validation and serialization."""

from typing import Optional, Literal, List
from datetime import datetime

from pydantic import BaseModel, HttpUrl, Field, validator


class DownloadRequest(BaseModel):
    """Request payload for initiating media download from supported SNS platforms."""

    url: HttpUrl = Field(
        ...,
        description="SNS media URL (Instagram, YouTube, TikTok, etc.)",
        examples=[
            "https://www.instagram.com/reel/ABC123/",
            "https://www.youtube.com/shorts/RN4U9Gw-NZ8",
            "https://www.instagram.com/p/ABC123/",
        ]
    )

    quality: Literal["high", "medium", "low"] = Field(
        default="high",
        description="Video quality preference (currently only 'high' is supported)"
    )

    @validator("url")
    def validate_sns_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure URL is from supported SNS platforms."""
        url_str = str(v)
        supported_domains = ["instagram.com", "youtube.com", "youtu.be", "tiktok.com", "twitter.com", "x.com"]

        if not any(domain in url_str for domain in supported_domains):
            raise ValueError(
                f"URL must be from supported platforms: {', '.join(supported_domains)}"
            )
        return v


class MediaMetadata(BaseModel):
    """Metadata about the downloaded media."""

    shortcode: str = Field(..., description="Instagram post shortcode")
    duration_seconds: Optional[int] = Field(None, description="Video duration in seconds")
    width: Optional[int] = Field(None, description="Video width in pixels")
    height: Optional[int] = Field(None, description="Video height in pixels")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")
    download_timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="When the download was completed"
    )


class DownloadResponse(BaseModel):
    """Successful download response with media URLs and metadata."""

    status: Literal["success"] = "success"
    media_url: str = Field(..., description="URL to access the downloaded media (video or photo)")
    media_urls: Optional[List[str]] = Field(None, description="Multiple media URLs for carousel posts")
    media_type: str = Field(..., description="Type of media: 'video', 'photo', or 'carousel'")
    thumbnail_url: Optional[str] = Field(None, description="URL to access the thumbnail (only for videos)")
    metadata: MediaMetadata = Field(..., description="Media metadata")

    # Text metadata fields
    metadata_url: Optional[str] = Field(None, description="URL to access full metadata JSON file")
    caption: Optional[str] = Field(None, description="Post caption/description text")
    hashtags: Optional[List[str]] = Field(None, description="Extracted hashtags from caption")
    mentions: Optional[List[str]] = Field(None, description="Extracted @mentions from caption")


class ErrorResponse(BaseModel):
    """Error response with details for debugging."""

    status: Literal["error"] = "error"
    error_type: str = Field(..., description="Error category (e.g., 'invalid_url', 'rate_limit')")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict] = Field(None, description="Additional error context")


class HealthCheckResponse(BaseModel):
    """Health check response for monitoring."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.utcnow())
    checks: dict = Field(
        default_factory=dict,
        description="Individual health check results"
    )
