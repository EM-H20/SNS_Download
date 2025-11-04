"""Unit tests for URL parsing functionality.

Tests cover various URL formats and edge cases to ensure robust parsing.
"""

import pytest
from app.parser import ReelsURLParser
from app.exceptions import InvalidURLError


class TestReelsURLParser:
    """Test suite for Instagram URL parsing."""

    def test_extract_shortcode_from_reel_url(self):
        """Standard /reel/ URL format."""
        url = "https://www.instagram.com/reel/ABC_123-xyz/"
        result = ReelsURLParser.extract_shortcode(url)
        assert result == "ABC_123-xyz"

    def test_extract_shortcode_from_post_url(self):
        """Legacy /p/ URL format (also used for video posts)."""
        url = "https://instagram.com/p/ABC_123-xyz/"
        result = ReelsURLParser.extract_shortcode(url)
        assert result == "ABC_123-xyz"

    def test_extract_shortcode_from_tv_url(self):
        """Legacy IGTV /tv/ URL format."""
        url = "https://www.instagram.com/tv/ABC_123-xyz/"
        result = ReelsURLParser.extract_shortcode(url)
        assert result == "ABC_123-xyz"

    def test_extract_shortcode_with_query_params(self):
        """URL with query parameters should be normalized."""
        url = "https://instagram.com/reel/ABC_123-xyz/?utm_source=test"
        result = ReelsURLParser.extract_shortcode(url)
        assert result == "ABC_123-xyz"

    def test_extract_shortcode_without_trailing_slash(self):
        """URL without trailing slash should work."""
        url = "https://instagram.com/reel/ABC_123-xyz"
        result = ReelsURLParser.extract_shortcode(url)
        assert result == "ABC_123-xyz"

    def test_invalid_url_empty_string(self):
        """Empty string should raise InvalidURLError."""
        with pytest.raises(InvalidURLError, match="non-empty string"):
            ReelsURLParser.extract_shortcode("")

    def test_invalid_url_wrong_domain(self):
        """Non-Instagram domain should raise InvalidURLError."""
        url = "https://youtube.com/watch?v=abc123"
        with pytest.raises(InvalidURLError, match="does not match"):
            ReelsURLParser.extract_shortcode(url)

    def test_invalid_url_wrong_path(self):
        """Instagram URL with wrong path should raise InvalidURLError."""
        url = "https://instagram.com/user/profile/"
        with pytest.raises(InvalidURLError, match="does not match"):
            ReelsURLParser.extract_shortcode(url)

    def test_invalid_shortcode_too_short(self):
        """Shortcode with wrong length should raise InvalidURLError."""
        url = "https://instagram.com/reel/ABC/"
        with pytest.raises(InvalidURLError, match="Invalid shortcode format"):
            ReelsURLParser.extract_shortcode(url)

    def test_validate_url_returns_true_for_valid(self):
        """validate_url should return True for valid URLs."""
        url = "https://instagram.com/reel/ABC_123-xyz/"
        assert ReelsURLParser.validate_url(url) is True

    def test_validate_url_returns_false_for_invalid(self):
        """validate_url should return False for invalid URLs."""
        url = "https://youtube.com/watch?v=abc"
        assert ReelsURLParser.validate_url(url) is False

    def test_normalize_url(self):
        """normalize_url should convert to canonical format."""
        url = "https://instagram.com/p/ABC_123-xyz/?utm=test"
        result = ReelsURLParser.normalize_url(url)
        assert result == "https://www.instagram.com/reel/ABC_123-xyz/"
