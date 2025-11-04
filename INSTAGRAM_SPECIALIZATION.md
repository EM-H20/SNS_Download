# Instagram Specialization System

## Overview

The Instagram downloader now features an intelligent **hybrid routing system** that automatically selects the best downloader based on content type:

- **yt-dlp**: For video Reels and video posts (no login required, fast)
- **Instaloader**: For photo posts and full carousel downloads (requires login, comprehensive)

## Architecture

```
User Request
     ↓
[URL Parser] → Extract shortcode
     ↓
[Media Analyzer] → Detect content type (video/photo/carousel)
     ↓
[Downloader Router] → Route to appropriate downloader
     ↓
[yt-dlp OR Instaloader] → Download media
     ↓
[Response] → Return media URLs
```

## Components

### 1. InstagramMediaAnalyzer ([app/media_analyzer.py](app/media_analyzer.py))

Analyzes Instagram content **before downloading** to determine:
- Media type: video, photo, or carousel
- Number of items in carousel
- Whether authentication is required

**How it works:**
```python
analyzer = InstagramMediaAnalyzer()
analysis = analyzer.analyze(shortcode)
# Returns:
# {
#   "media_type": "video" | "photo" | "carousel",
#   "is_carousel": boolean,
#   "item_count": int,
#   "requires_login": boolean
# }
```

### 2. InstagramDownloaderRouter ([app/downloader_router.py](app/downloader_router.py))

Routes downloads based on analysis results:

| Content Type | Downloader | Login Required | Reason |
|-------------|-----------|----------------|---------|
| Video Reel | yt-dlp | ❌ No | Fast, stable, no auth needed |
| Video Post | yt-dlp | ❌ No | Fast, stable, no auth needed |
| Photo Post | Instaloader | ✅ Yes | yt-dlp doesn't support photos |
| Carousel (full) | Instaloader | ✅ Yes | yt-dlp only gets first item |

**Smart Fallback:**
- If credentials not configured and photo/carousel requested → returns helpful error message
- If credentials configured → uses Instaloader with full support

## Configuration

### Basic Setup (Video Only)

No configuration needed! Videos work out of the box:

```bash
# Start server
./run.sh

# Download video Reel (no login)
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/ABC123/"}'
```

### Advanced Setup (Photo + Carousel Support)

**⚠️ Important:** Use a test account, NOT your main Instagram account!

1. Create `.env` file:
```bash
# Instagram Authentication (Optional - for photos/carousels)
INSTAGRAM_USERNAME=your_test_account
INSTAGRAM_PASSWORD=your_test_password

# Other settings...
SERVER_HOST=127.0.0.1
SERVER_PORT=8000
DOWNLOAD_DIR=./downloads
RATE_LIMIT_PER_MINUTE=10
```

2. Restart server:
```bash
./run.sh
```

3. Verify capabilities:
```bash
curl http://localhost:8000/api/capabilities
```

## Usage Examples

### 1. Download Video Reel (No Login)

```bash
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.instagram.com/reel/DLwsg7BPmpL/",
    "quality": "high"
  }'
```

**Response:**
```json
{
  "status": "success",
  "media_url": "/downloads/DLwsg7BPmpL/2025-11-05_DLwsg7BPmpL.mp4",
  "media_type": "video",
  "thumbnail_url": "/downloads/DLwsg7BPmpL/2025-11-05_DLwsg7BPmpL_thumb.jpg",
  "metadata": {
    "shortcode": "DLwsg7BPmpL",
    "duration_seconds": 21,
    "width": 1080,
    "height": 1920,
    "size_bytes": 4456789
  }
}
```

### 2. Download Photo Post (Requires Login)

**Without credentials:**
```bash
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/p/DQnQfUGE6jR/"}'
```

**Response (Error):**
```json
{
  "status": "error",
  "error_type": "download_failed",
  "message": "This is a photo post. yt-dlp does not support Instagram photos. To download photos, configure Instagram credentials in .env file...",
  "details": {
    "shortcode": "DQnQfUGE6jR",
    "media_type": "photo",
    "solution": "Configure INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env file"
  }
}
```

**With credentials (successful):**
```json
{
  "status": "success",
  "media_url": "/downloads/DQnQfUGE6jR/2025-11-05_DQnQfUGE6jR.jpg",
  "media_type": "photo",
  "metadata": {
    "shortcode": "DQnQfUGE6jR",
    "size_bytes": 234567
  }
}
```

### 3. Download Carousel Post (Full Download Requires Login)

**Without credentials (first item only):**
```bash
curl -X POST "http://localhost:8000/api/download" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/p/DQOds_LD5Yc/"}'
```

**Response:**
```json
{
  "status": "error",
  "error_type": "download_failed",
  "message": "This is a carousel post with multiple items. yt-dlp can only download the first item. To download all items, configure Instagram credentials...",
  "details": {
    "shortcode": "DQOds_LD5Yc",
    "is_carousel": true,
    "solution": "See CAROUSEL_SUPPORT.md for details"
  }
}
```

**With credentials (all items):**
```json
{
  "status": "success",
  "media_url": "/downloads/DQOds_LD5Yc/2025-11-05_DQOds_LD5Yc_1.jpg",
  "media_urls": [
    "/downloads/DQOds_LD5Yc/2025-11-05_DQOds_LD5Yc_1.jpg",
    "/downloads/DQOds_LD5Yc/2025-11-05_DQOds_LD5Yc_2.jpg",
    "/downloads/DQOds_LD5Yc/2025-11-05_DQOds_LD5Yc_3.jpg"
  ],
  "media_type": "carousel",
  "metadata": {
    "shortcode": "DQOds_LD5Yc",
    "size_bytes": 789012
  }
}
```

## API Capabilities Endpoint

Check what features are currently enabled:

```bash
curl http://localhost:8000/api/capabilities
```

**Response (without credentials):**
```json
{
  "capabilities": {
    "video_reels": true,
    "video_posts": true,
    "photo_posts": false,
    "carousel_full": false,
    "carousel_first_item": true,
    "requires_authentication": true,
    "authenticated": false
  },
  "note": "Photo and full carousel support require Instagram credentials in .env"
}
```

**Response (with credentials):**
```json
{
  "capabilities": {
    "video_reels": true,
    "video_posts": true,
    "photo_posts": true,
    "carousel_full": true,
    "carousel_first_item": true,
    "requires_authentication": false,
    "authenticated": true
  }
}
```

## Benefits of Specialization

### 1. **No Authentication for Videos**
- Faster downloads (no login overhead)
- No account suspension risk
- Works immediately out of the box

### 2. **Optional Full Feature Support**
- Enable photo/carousel support only when needed
- Uses separate test account to protect main account
- Clear capability detection via API

### 3. **Intelligent Error Messages**
- User-friendly messages explain why content can't be downloaded
- Provides exact solution (configure credentials)
- Links to documentation for setup

### 4. **Optimal Performance**
- yt-dlp for videos: Fast, battle-tested, no auth overhead
- Instaloader for photos: Comprehensive, supports all formats
- Each tool used for its strengths

### 5. **Graceful Degradation**
- Without credentials: Videos still work perfectly
- With credentials: Full feature support
- Clear capability advertisement via `/api/capabilities`

## Security Considerations

### ⚠️ Instagram Account Safety

**DO NOT use your main Instagram account!**

Why:
- Instagram detects automated access
- Account suspension risk is REAL
- Bot detection may trigger 2FA challenges
- Rate limiting affects the account

**Best Practices:**
1. Create dedicated test account for API use
2. Use throwaway email address
3. Disable 2-factor authentication on test account
4. Respect rate limits (default: 10 requests/min)
5. Monitor for suspension warnings
6. Keep credentials in `.env` (never commit to git)

### Environment Security

The `.gitignore` already excludes sensitive files:
```
# Environment and secrets
.env
.env.local
.env.*.local
```

## Troubleshooting

### "Photo posts require Instagram credentials"

**Cause:** Attempting to download photo post without Instaloader

**Solution:**
1. Create test Instagram account
2. Add credentials to `.env`:
   ```
   INSTAGRAM_USERNAME=test_account
   INSTAGRAM_PASSWORD=test_password
   ```
3. Restart server: `./run.sh`

### "Carousel post - only first item downloaded"

**Cause:** yt-dlp limitation without authentication

**Solution:** Same as above - configure credentials

### "Instagram login failed"

**Causes:**
- 2FA enabled → Disable 2FA on test account
- Wrong credentials → Double-check `.env` file
- Account locked → Use different test account
- Rate limited → Wait and try again

### "Account suspended"

**Prevention:**
- Lower `RATE_LIMIT_PER_MINUTE` in `.env`
- Use only for testing/personal use
- Never use main account
- Consider adding delays between requests

## Comparison Table

| Feature | Without Credentials | With Credentials |
|---------|-------------------|------------------|
| Video Reels | ✅ Full support | ✅ Full support |
| Video Posts | ✅ Full support | ✅ Full support |
| Photo Posts | ❌ Not supported | ✅ Supported |
| Carousel (first item) | ⚠️ Limited | ✅ Full download |
| Carousel (all items) | ❌ Not supported | ✅ Supported |
| Setup Time | Immediate | ~5 minutes |
| Account Risk | None | Test account only |
| Speed | Fast (yt-dlp) | Moderate (mixed) |

## Future Enhancements

Potential improvements:

1. **Automatic Fallback**
   - Try yt-dlp first
   - Fall back to Instaloader if needed
   - Transparent to user

2. **Selective Item Download**
   - Support `?img_index=N` parameter
   - Download specific carousel items
   - User choice of items

3. **Session Persistence**
   - Cache Instaloader sessions
   - Reduce login frequency
   - Improve performance

4. **User-Provided Credentials**
   - Allow per-request authentication
   - OAuth integration
   - No server-side credential storage

## Related Documentation

- [CAROUSEL_SUPPORT.md](CAROUSEL_SUPPORT.md) - Detailed carousel handling guide
- [CLAUDE.md](CLAUDE.md) - Project architecture and development guide
- [README.md](README.md) - General usage and setup instructions
- [QUICK_START.md](QUICK_START.md) - Fast setup guide

## Technical Details

### File Structure
```
app/
├── media_analyzer.py        # Content type detection
├── downloader_router.py     # Intelligent routing
├── downloader.py            # yt-dlp implementation
├── downloader_instaloader.py # Instaloader implementation
├── parser.py                # URL parsing
├── main.py                  # FastAPI app with router
└── config.py                # Settings management
```

### Request Flow

1. **Parse URL** → Extract shortcode
2. **Analyze Content** → Detect type (video/photo/carousel)
3. **Check Credentials** → Determine available downloaders
4. **Route Decision**:
   - Video + no auth needed → yt-dlp
   - Photo/Carousel + auth needed → Check credentials
     - If available → Instaloader
     - If not → Error with helpful message
5. **Download** → Execute with selected downloader
6. **Return** → Media URLs and metadata

### Performance Characteristics

| Operation | yt-dlp | Instaloader |
|-----------|--------|-------------|
| Analysis | ~1-2s | ~2-3s |
| Video Download | ~3-5s | ~5-7s |
| Photo Download | N/A | ~2-3s |
| Carousel (3 items) | First only | ~5-8s |
| Memory Usage | Low | Moderate |
| CPU Usage | Low | Low |

## Conclusion

The specialized Instagram system provides:
- ✅ Zero-config video downloads
- ✅ Optional photo/carousel support
- ✅ Intelligent routing based on content type
- ✅ Clear capability advertisement
- ✅ Helpful error messages with solutions
- ✅ Security-conscious design
- ✅ Optimal performance per content type

For video-only use cases, no setup is needed. For full feature support, simply add test account credentials to `.env` and restart the server.
