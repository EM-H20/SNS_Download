# Instagram Reels Downloader API

Production-grade Python FastAPI server for downloading Instagram Reels from public accounts without authentication.

## ⚠️ Important Legal Notice

**This tool is for educational purposes only.**

- ✅ Only works with **public accounts**
- ✅ For **personal, non-commercial use** only
- ❌ Respect Instagram's Terms of Service
- ❌ Do not use for content redistribution or commercial purposes
- ❌ Respect content creators' intellectual property rights

## 🎯 Features

- **No Authentication Required**: Download from public accounts without login
- **Rate Limited**: Prevents abuse and protects Instagram's API
- **Multiple URL Formats**: Supports `/reel/`, `/p/`, `/tv/` URLs
- **Robust Error Handling**: Clear error messages for different failure scenarios
- **Production Ready**: Comprehensive logging, health checks, monitoring
- **Type Safe**: Full Pydantic validation and type hints

## 🏗️ Architecture

```
app/
├── main.py          # FastAPI application with endpoints
├── downloader.py    # Core download engine (Instaloader)
├── parser.py        # URL parsing and validation
├── models.py        # Pydantic request/response models
├── config.py        # Configuration management
└── exceptions.py    # Custom exception hierarchy
```

**Strategy**: Primary method uses `instaloader` library for fast, reliable downloads without browser overhead.

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local development)
```

### 4. Start Server

```bash
# Using startup script (recommended)
chmod +x run.sh
./run.sh

# Or directly with uvicorn
python -m uvicorn app.main:app --reload
```

Server will start at: `http://localhost:8000`

## 📖 API Documentation

### Interactive Docs

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Endpoints

#### POST `/api/download`

Download Instagram Reels video.

**Request Body:**
```json
{
  "url": "https://www.instagram.com/reel/ABC123/",
  "quality": "high"
}
```

**Success Response (200):**
```json
{
  "status": "success",
  "video_url": "/downloads/ABC123/2024-01-01_ABC123.mp4",
  "thumbnail_url": "/downloads/ABC123/2024-01-01_ABC123.jpg",
  "metadata": {
    "shortcode": "ABC123",
    "duration_seconds": 15,
    "width": 1080,
    "height": 1920,
    "size_bytes": 2458624,
    "download_timestamp": "2024-01-01T12:00:00"
  }
}
```

**Error Responses:**

| Status | Error Type | Description |
|--------|------------|-------------|
| 400 | `invalid_url` | URL format is invalid |
| 403 | `private_account` | Content is from a private account |
| 404 | `content_not_found` | Content doesn't exist or was deleted |
| 429 | `rate_limit_exceeded` | Too many requests, retry later |
| 500 | `download_failed` | Download failed after retries |
| 503 | `instagram_api_error` | Instagram API structure changed |

#### GET `/health`

Health check for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00",
  "checks": {
    "download_dir_writable": true,
    "instaloader_initialized": true
  }
}
```

## 🧪 Testing

### Run Unit Tests

```bash
pytest tests/ -v
```

### Test URL Parser

```bash
pytest tests/test_parser.py -v
```

### Manual Testing with curl

```bash
# Download a Reels video
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/ABC123/"
  }'

# Health check
curl http://localhost:8000/health
```

## 📊 Configuration

Edit `.env` file to customize behavior:

```bash
# Server
SERVER_HOST=127.0.0.1
SERVER_PORT=8000

# Storage
DOWNLOAD_DIR=./downloads
MAX_FILE_SIZE_MB=100

# Rate Limiting (requests per minute per IP)
RATE_LIMIT_PER_MINUTE=10

# Instagram Scraping
REQUEST_TIMEOUT_SECONDS=30
MAX_RETRIES=3
```

## 🔧 Troubleshooting

### "LoginRequiredException" for public posts

**Cause**: Instagram may have changed their API structure
**Solution**: Update `instaloader` library: `pip install --upgrade instaloader`

### "Rate limit exceeded" errors

**Cause**: Too many requests to Instagram
**Solution**: Increase `RATE_LIMIT_PER_MINUTE` or wait before retrying

### Video file not found after download

**Cause**: Instaloader naming convention changed
**Solution**: Check `app/downloader.py` file naming pattern

### Private account errors

**Expected behavior**: This is by design. The API only works with public accounts.

## 🏭 Production Deployment

### Recommended Setup

1. **Reverse Proxy**: Use nginx/caddy in front of uvicorn
2. **Process Manager**: Use systemd/supervisor for auto-restart
3. **Rate Limiting**: Configure at nginx level for additional protection
4. **Storage**: Mount persistent volume for `downloads/` directory
5. **Monitoring**: Use health check endpoint for uptime monitoring

### Environment Variables

```bash
ENVIRONMENT=production
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### Run with Production Server

```bash
# Install production dependencies
pip install gunicorn

# Run with gunicorn (4 workers)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile -
```

## 🛠️ Technology Stack

- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn (ASGI)
- **Scraping**: Instaloader 4.10+
- **Validation**: Pydantic V2
- **Rate Limiting**: SlowAPI
- **Testing**: pytest

## 📝 Development Notes

### Code Style

- **Type Hints**: Full type annotations on all functions
- **Docstrings**: Google-style docstrings for public APIs
- **Comments**: Only where intent is not obvious from code
- **Error Handling**: Specific exception types, not bare except

### Adding New Features

1. Add exception type in `app/exceptions.py`
2. Add request/response model in `app/models.py`
3. Implement business logic in respective module
4. Add endpoint in `app/main.py`
5. Write tests in `tests/`

## 🤝 Contributing

This is an educational project. Contributions should:

- Maintain legal compliance
- Include tests for new features
- Follow existing code style
- Update documentation

## 📄 License

Educational use only. See legal notice above.

## 🔗 References

- [Instaloader Documentation](https://instaloader.github.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Instagram Terms of Service](https://help.instagram.com/581066165581870)
