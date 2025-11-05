# Instagram Authentication Guide

## Overview

Instagram has implemented comprehensive bot detection and blocking as of late 2024. **All automated download methods now require authentication**, including:

- ✅ **Instaloader** (Recommended - Already implemented)
- ❌ yt-dlp (Only videos, auth required)
- ❌ gallery-dl (All types, auth required)
- ❌ Instagram GraphQL API (Auth required)
- ❌ HTML Scraping (Redirects to login)

## Current Implementation Status

### What Works WITHOUT Authentication
- **Nothing** - Instagram blocks all unauthenticated automation

### What Works WITH Authentication (Instaloader)
- ✅ Videos and Reels
- ✅ Photos (single images)
- ✅ Carousel posts (multiple images/videos)
- ✅ Rich metadata (captions, hashtags, mentions, engagement)
- ✅ Comments collection (optional)

## Setup Instructions

### Step 1: Create Instagram Test Account

**IMPORTANT**: Do NOT use your personal Instagram account. Create a dedicated test account.

**Why?**
- Risk of account restrictions or bans
- Instagram's anti-bot measures may flag automated access
- Separate test account protects your personal data

**How to Create Test Account**:
1. Go to https://www.instagram.com/accounts/emailsignup/
2. Use a dedicated email (e.g., `yourname.dev@gmail.com`)
3. Username: Something like `yourname_api_test`
4. Strong password (store in password manager)
5. Complete profile setup (adds legitimacy)
6. Follow 10-20 accounts (makes it look like a real account)

### Step 2: Configure Environment Variables

Add Instagram credentials to your `.env` file:

```bash
# Instagram Authentication (for Instaloader - photo/carousel support)
INSTAGRAM_USERNAME=your_test_account_username
INSTAGRAM_PASSWORD=your_secure_password
```

**Security Best Practices**:
- Never commit `.env` to version control
- Use strong, unique password
- Consider using Instagram App Password (if available)
- Store credentials in secure password manager

### Step 3: Verify Configuration

The application will automatically detect credentials and enable Instaloader:

```bash
# Start server
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# You should see this in logs:
# INFO: Instagram authentication enabled for user: your_test_account_username
```

### Step 4: Test Downloads

Test with various content types:

#### Video/Reel Test
```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/reel/ABC123/"}'
```

#### Photo Test
```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/p/XYZ789/"}'
```

#### Carousel Test (Multiple Images)
```bash
curl -X POST http://localhost:8000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.instagram.com/p/DEF456/?img_index=1"}'
```

## Rate Limiting & Best Practices

### Instagram's Limits

Instagram monitors automated activity and may:
- Temporarily restrict your account (few hours to days)
- Require CAPTCHA verification
- Permanently ban repeat offenders

### Safe Usage Guidelines

**Recommended Limits**:
- **Requests per minute**: 3-5 maximum
- **Requests per hour**: 50-100 maximum
- **Daily downloads**: 500-1000 maximum
- **Add delays**: 10-20 seconds between requests

**Current Implementation**:
```python
# In app/config.py
rate_limit_per_minute: int = 10  # Consider reducing to 3-5
```

**Recommendations**:
1. Reduce `rate_limit_per_minute` to 3-5
2. Add exponential backoff on errors
3. Implement request queuing with delays
4. Monitor for Instagram error responses

### Account Safety Checklist

✅ **Do**:
- Use dedicated test account
- Start with low request rates
- Add delays between requests
- Monitor for Instagram warnings
- Respect rate limits strictly
- Test during off-peak hours

❌ **Don't**:
- Use personal Instagram account
- Make rapid consecutive requests
- Download thousands of posts daily
- Ignore Instagram error responses
- Share credentials in code
- Use same account for multiple services

## Troubleshooting

### Login Failures

**Error**: `Login error: Bad credentials or challenge required`

**Solutions**:
1. Verify username/password in `.env`
2. Try logging in manually via browser
3. Complete any required verifications
4. Wait 24 hours if account restricted
5. Try different test account

### Rate Limiting Errors

**Error**: `Rate limit exceeded, please try again later`

**Solutions**:
1. Reduce request frequency
2. Implement longer delays
3. Use request queuing system
4. Distribute requests across time

### Challenge Required

**Error**: `Challenge required (CAPTCHA or verification)`

**Solutions**:
1. Login manually via browser
2. Complete verification process
3. Wait before resuming automation
4. Consider using browser session cookies

## Alternative Solutions

If Instaloader authentication proves problematic:

### Option 1: Browser Automation (Playwright)
- Mimics human browser behavior
- Can maintain login session
- More resource-intensive
- Lower ban risk

### Option 2: Paid API Services
- **RapidAPI Instagram APIs**: $10-50/month
- Stable, no account ban risk
- Official API access
- Suitable for production

### Option 3: Manual Session Management
- Extract Instagram session cookies manually
- Use cookies in requests
- Requires periodic refresh
- More complex implementation

## Metadata Collection

With authentication enabled, you get rich metadata:

```json
{
  "post": {
    "shortcode": "ABC123",
    "caption": "Post caption with #hashtags and @mentions",
    "hashtags": ["hashtag1", "hashtag2"],
    "mentions": ["username1", "username2"],
    "is_video": true,
    "is_carousel": false
  },
  "engagement": {
    "likes": 1234,
    "comments_count": 56,
    "views": 5678
  },
  "author": {
    "username": "author_username",
    "full_name": "Author Name",
    "is_verified": false
  },
  "collected_at": "2025-11-05T01:00:00Z"
}
```

## Next Steps

1. **Create Instagram test account**
2. **Add credentials to `.env`**
3. **Restart server and verify logs**
4. **Test with sample URLs**
5. **Monitor rate limits and adjust**
6. **Document any issues encountered**

## Support

If you encounter issues:
1. Check server logs for detailed errors
2. Verify credentials are correctly set
3. Test manual login via browser
4. Consider alternative solutions listed above
5. Create issue in project repository
