"""Platform-specific downloaders for different social media services."""

from .base import BasePlatform, PlatformType
from .instagram import InstagramPlatform
from .youtube import YouTubePlatform

__all__ = [
    'BasePlatform',
    'PlatformType',
    'InstagramPlatform',
    'YouTubePlatform',
]
