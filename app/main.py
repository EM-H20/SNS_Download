"""FastAPI application for Instagram Reels downloading.

Production-ready server with:
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
from app.parser import ReelsURLParser
from app.downloader_router import InstagramDownloaderRouter
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
    title="Instagram Media Downloader API",
    description="Download Instagram Reels, videos, photos, and carousels with intelligent routing",
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

# Initialize intelligent router (automatically selects yt-dlp or Instaloader)
downloader = InstagramDownloaderRouter()
parser = ReelsURLParser()


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
        "downloader_initialized": downloader is not None,
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
        400: {"model": ErrorResponse, "description": "Invalid URL format"},
        403: {"model": ErrorResponse, "description": "Private account or forbidden"},
        404: {"model": ErrorResponse, "description": "Content not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Download failed"},
        503: {"model": ErrorResponse, "description": "Instagram API error"},
    },
    tags=["Download"],
    summary="Download Instagram media (Reels, videos, photos, carousels)"
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def download_reels(request: Request, payload: DownloadRequest):
    """Download Instagram media with intelligent routing.

    **Supported Content Types**:
    - Video Reels (no login required)
    - Regular video posts (no login required)
    - Photo posts (requires Instagram credentials)
    - Carousel posts (requires Instagram credentials for full download)

    **Authentication**:
    - Videos: No authentication needed, uses yt-dlp
    - Photos/Carousels: Requires Instagram credentials in .env file, uses Instaloader

    **Rate Limiting**: Limited to {settings.rate_limit_per_minute} requests per minute per IP.

    **Response**: Returns URLs to access downloaded media. For carousels, returns array of URLs.
    """
    try:
        # Extract shortcode from URL
        shortcode = parser.extract_shortcode(str(payload.url))
        logger.info(f"Processing download request for shortcode: {shortcode}")

        # Download using intelligent router (returns media_path(s), thumbnail, metadata, type)
        result = downloader.download(shortcode)
        media_paths, thumbnail_path, metadata, media_type = result

        # Handle single vs multiple media files
        if isinstance(media_paths, list):
            # Carousel - multiple files
            media_urls = [f"/downloads/{shortcode}/{p.name}" for p in media_paths]
            primary_url = media_urls[0]
        else:
            # Single file
            primary_url = f"/downloads/{shortcode}/{media_paths.name}"
            media_urls = [primary_url]

        # Generate thumbnail URL
        thumbnail_url = f"/downloads/{shortcode}/{thumbnail_path.name}" if thumbnail_path else None

        return DownloadResponse(
            media_url=primary_url,
            media_urls=media_urls if len(media_urls) > 1 else None,
            media_type=media_type,
            thumbnail_url=thumbnail_url,
            metadata=metadata
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


@app.get(
    "/api/capabilities",
    tags=["Info"],
    summary="Get downloader capabilities"
)
async def get_capabilities():
    """Get current API capabilities based on configuration."""
    capabilities = downloader.get_capabilities()
    return {
        "capabilities": capabilities,
        "note": "Photo and full carousel support require Instagram credentials in .env"
    }


@app.get(
    "/",
    tags=["Info"],
    summary="API information"
)
async def root():
    """Get API information and usage instructions."""
    capabilities = downloader.get_capabilities()

    return {
        "name": "Instagram Media Downloader API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
        "capabilities": "/api/capabilities",
        "endpoints": {
            "download": "POST /api/download",
            "access_media": "GET /downloads/{shortcode}/{filename}"
        },
        "features": {
            "video_reels": "✅ Supported (no login)",
            "video_posts": "✅ Supported (no login)",
            "photo_posts": "✅ Supported (requires login)" if capabilities["photo_posts"] else "❌ Requires Instagram credentials",
            "carousel_posts": "✅ Full download (requires login)" if capabilities["carousel_full"] else "⚠️ First item only (full support requires credentials)"
        },
        "usage": {
            "example_request": {
                "url": "https://www.instagram.com/reel/ABC123/",
                "quality": "high"
            },
            "authentication": "Configure INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env for photo/carousel support"
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
