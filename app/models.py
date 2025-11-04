"""Pydantic models for request/response validation and serialization."""

from typing import Optional, Literal, List
from datetime import datetime

from pydantic import BaseModel, HttpUrl, Field, validator


class DownloadRequest(BaseModel):
    """Request payload for initiating a Reels download."""

    url: HttpUrl = Field(
        ...,
        description="Instagram Reels URL (e.g., https://instagram.com/reel/ABC123/)",
        examples=["https://www.instagram.com/reel/ABC123/"]
    )

    quality: Literal["high", "medium", "low"] = Field(
        default="high",
        description="Video quality preference (currently only 'high' is supported)"
    )

    @validator("url")
    def validate_instagram_url(cls, v: HttpUrl) -> HttpUrl:
        """Ensure URL is from Instagram domain."""
        if "instagram.com" not in str(v):
            raise ValueError("URL must be from instagram.com domain")
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
