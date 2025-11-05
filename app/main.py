"""FastAPI application for Universal SNS Media Downloader.

Production-ready server with:
- Multi-platform support (Instagram, YouTube, TikTok, etc.)
- Rate limiting per IP
- Comprehensive error handling
- Static file serving for downloaded media
- Health checks for monitoring
- CORS support for web clients
"""

import logging
from pathlib import Path
from typing import Union

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.config import settings
from app.models import (
    DownloadRequest,
    DownloadResponse,
    ErrorResponse,
    HealthCheckResponse,
)
from app.universal_downloader import UniversalDownloader
from app.metadata_storage import MetadataStorage
from app.temp_storage import temp_storage
from app.ai_analyzer import video_analyzer, analyze_and_cleanup
from app.exceptions import (
    ReelsDownloaderError,
    InvalidURLError,
    PrivateAccountError,
    ContentNotFoundError,
    RateLimitExceededError,
    DownloadFailedError,
    InstagramAPIError,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Universal SNS Media Downloader API",
    description="Download media from Instagram, YouTube, TikTok, and more",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting - protects both our server and Instagram's API
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - allow web clients to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving downloaded media
if settings.download_dir.exists():
    app.mount(
        "/downloads",
        StaticFiles(directory=str(settings.download_dir)),
        name="downloads"
    )

# Initialize universal downloader (supports all platforms)
universal_downloader = UniversalDownloader()


@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Monitoring"],
    summary="Health check endpoint for monitoring"
)
async def health_check():
    """Check service health and dependencies."""
    checks = {
        "download_dir_writable": settings.download_dir.exists() and settings.download_dir.is_dir(),
        "downloader_initialized": universal_downloader is not None,
        "supported_platforms": len(universal_downloader.get_supported_platforms()),
    }

    status_value = "healthy" if all(checks.values()) else "degraded"

    return HealthCheckResponse(
        status=status_value,
        version=__version__,
        checks=checks
    )


@app.post(
    "/api/download",
    response_model=DownloadResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL or unsupported platform"},
        403: {"model": ErrorResponse, "description": "Private account or forbidden"},
        404: {"model": ErrorResponse, "description": "Content not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Download failed"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    tags=["Download"],
    summary="Download media from Instagram, YouTube, and more"
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def download_media(request: Request, payload: DownloadRequest):
    """Download media from supported SNS platforms.

    **Supported Platforms**:
    - Instagram (Reels, videos, photos, carousels)
    - YouTube (videos, shorts)
    - TikTok (coming soon)
    - Twitter (coming soon)

    **Rate Limiting**: Limited to {settings.rate_limit_per_minute} requests per minute per IP.

    **Response**: Returns URLs to access the downloaded media and thumbnail (if applicable).
    """
    try:
        # Download using universal downloader (auto-detects platform)
        url_str = str(payload.url)
        logger.info(f"Processing download request for URL: {url_str}")

        # Download media using universal downloader
        media_path, thumbnail_path, metadata, platform_name = universal_downloader.download(url_str)

        # Determine media type from file extension
        media_type = "video" if media_path.suffix.lower() in ['.mp4', '.webm', '.mkv'] else "photo"

        # Extract identifier for URL generation
        identifier = media_path.parent.name

        # Generate access URLs (relative to our server)
        media_url = f"/downloads/{identifier}/{media_path.name}"
        thumbnail_url = f"/downloads/{identifier}/{thumbnail_path.name}" if thumbnail_path else None

        # Load metadata summary if available (Instagram only for now)
        metadata_summary = None
        metadata_url = None
        if platform_name == "instagram" and settings.save_metadata:
            metadata_summary = MetadataStorage.get_metadata_summary(metadata.shortcode)
            if metadata_summary:
                metadata_url = f"/downloads/{identifier}/{metadata.shortcode}_metadata.json"

        return DownloadResponse(
            media_url=media_url,
            media_type=media_type,
            thumbnail_url=thumbnail_url,
            metadata=metadata,
            metadata_url=metadata_url,
            caption=metadata_summary.get("caption") if metadata_summary else None,
            hashtags=metadata_summary.get("hashtags") if metadata_summary else None,
            mentions=metadata_summary.get("mentions") if metadata_summary else None
        )

    except InvalidURLError as e:
        logger.warning(f"Invalid URL: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                error_type="invalid_url",
                message=e.message,
                details=e.details
            ).dict()
        )

    except PrivateAccountError as e:
        logger.warning(f"Private account access attempt: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(
                error_type="private_account",
                message=e.message,
                details=e.details
            ).dict()
        )

    except ContentNotFoundError as e:
        logger.warning(f"Content not found: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(
                error_type="content_not_found",
                message=e.message,
                details=e.details
            ).dict()
        )

    except RateLimitExceededError as e:
        logger.warning(f"Instagram rate limit hit: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=ErrorResponse(
                error_type="rate_limit_exceeded",
                message=e.message,
                details=e.details
            ).dict()
        )

    except InstagramAPIError as e:
        logger.error(f"Instagram API error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorResponse(
                error_type="instagram_api_error",
                message=e.message,
                details=e.details
            ).dict()
        )

    except (DownloadFailedError, ReelsDownloaderError) as e:
        logger.error(f"Download failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_type="download_failed",
                message=e.message,
                details=e.details
            ).dict()
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_type="internal_error",
                message="An unexpected error occurred",
                details={"error": str(e)}
            ).dict()
        )


@app.post(
    "/api/analyze",
    tags=["AI Analysis"],
    summary="Download video, analyze with AI, then delete (legal AI workflow)"
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def analyze_video(request: Request, payload: DownloadRequest):
    """AI Analysis Workflow: Download → Analyze → Delete (Fair Use Compliant).

    **Legal AI Analysis Workflow**:
    1. Download video temporarily
    2. Analyze with AI (extract text, transcript, description)
    3. Delete video file
    4. Return analysis result (text only)

    This workflow complies with fair use for transformative AI analysis.
    No permanent video storage, only text analysis results.

    **Supported Platforms**: YouTube, Instagram (with auth)

    **Rate Limiting**: Limited to {settings.rate_limit_per_minute} requests per minute per IP.

    **Response**: Returns AI analysis results (text) without video file.
    """
    try:
        url_str = str(payload.url)
        logger.info(f"Processing AI analysis request for URL: {url_str}")

        # Download video temporarily
        media_path, thumbnail_path, metadata, platform_name = universal_downloader.download(url_str)

        # Only analyze videos (not photos)
        if media_path.suffix.lower() not in ['.mp4', '.webm', '.mkv']:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    error_type="invalid_media_type",
                    message="AI analysis only supports video files",
                    details={"media_type": "photo", "file": str(media_path)}
                ).dict()
            )

        # Analyze video and delete it
        analysis_result = analyze_and_cleanup(media_path)

        # Return analysis result (no video URL, only text)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "platform": platform_name,
                "analysis": analysis_result.to_dict(),
                "note": "Video was analyzed and deleted (fair use compliance)"
            }
        )

    except Exception as e:
        logger.exception(f"AI analysis failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_type="analysis_failed",
                message=f"AI analysis failed: {str(e)}",
                details={"error": str(e)}
            ).dict()
        )


@app.get(
    "/api/media/webview",
    tags=["Webview"],
    summary="Get direct media URLs for webview display (photos/thumbnails)"
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_webview_media_url(request: Request, url: str):
    """Get direct media URLs for webview display without downloading.

    **Use Case**: Display photos and thumbnails in webview without server storage.

    For photos/thumbnails: Returns direct Instagram/YouTube URLs
    For videos: Use /api/analyze endpoint instead (AI workflow)

    **Legal Approach**:
    - Photos/Thumbnails: Direct URLs (no download, webview display only)
    - Videos: Use /api/analyze for AI analysis → text extraction → deletion

    **Query Parameters**:
    - url: SNS media URL (Instagram, YouTube, etc.)

    **Response**: Returns direct media URLs for webview display
    """
    try:
        logger.info(f"Processing webview URL request for: {url}")

        # Detect platform
        platform = universal_downloader.detect_platform(url)

        if not platform:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=ErrorResponse(
                    error_type="unsupported_platform",
                    message="Unsupported platform or invalid URL",
                    details={"url": url}
                ).dict()
            )

        # Extract identifier
        identifier = platform.extract_identifier(url)

        # Return platform info and guidance
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "platform": platform.platform_name.value,
                "identifier": identifier,
                "original_url": url,
                "guidance": {
                    "photos_thumbnails": "Use Instagram embed API or direct URLs in webview",
                    "videos": "Use /api/analyze endpoint for AI analysis workflow",
                    "note": "For webview display, embed original URLs directly without downloading"
                },
                "instagram_embed_url": f"https://www.instagram.com/p/{identifier}/embed" if "instagram" in url else None,
                "youtube_embed_url": f"https://www.youtube.com/embed/{identifier}" if "youtube" in url or "youtu.be" in url else None
            }
        )

    except Exception as e:
        logger.exception(f"Webview URL processing failed: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_type="processing_failed",
                message=f"Failed to process webview URL: {str(e)}",
                details={"error": str(e)}
            ).dict()
        )


@app.get(
    "/api/temp-storage/stats",
    tags=["Monitoring"],
    summary="Get temporary storage statistics"
)
async def get_temp_storage_stats():
    """Get temporary storage statistics and cleanup status.

    **Returns**:
    - Total temporary files
    - Total storage used
    - Cleanup settings
    """
    stats = temp_storage.get_storage_stats()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "storage": stats,
            "cleanup": {
                "enabled": True,
                "cleanup_after_seconds": temp_storage.cleanup_after_seconds,
                "cleanup_after_minutes": temp_storage.cleanup_after_seconds / 60
            }
        }
    )


@app.get(
    "/",
    tags=["Info"],
    summary="API information"
)
async def root():
    """Get API information and usage instructions."""
    return {
        "name": "Universal SNS Media Downloader & AI Analysis API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "download": "POST /api/download - Download and serve media files",
            "ai_analysis": "POST /api/analyze - AI analysis workflow (download → analyze → delete)",
            "webview_urls": "GET /api/media/webview?url=... - Get embed URLs for webview",
            "temp_stats": "GET /api/temp-storage/stats - Temporary storage statistics",
            "access_media": "GET /downloads/{shortcode}/{filename} - Access downloaded files"
        },
        "legal_workflow": {
            "videos": "Use /api/analyze for AI analysis (fair use compliant)",
            "photos": "Use /api/media/webview for direct embed URLs"
        },
        "supported_platforms": [p["platform"] for p in universal_downloader.get_supported_platforms()],
        "usage": {
            "ai_analysis_example": {
                "url": "https://www.youtube.com/shorts/RN4U9Gw-NZ8",
                "note": "Video will be analyzed and deleted automatically"
            },
            "webview_example": {
                "url": "https://www.instagram.com/p/ABC123/",
                "note": "Returns embed URL for webview display"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.environment == "development",
        log_level="info"
    )
