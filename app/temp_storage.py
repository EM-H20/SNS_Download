"""Temporary storage management for downloaded videos.

Implements secure temporary storage with automatic cleanup for AI analysis workflow.
Videos are downloaded temporarily, analyzed, then automatically deleted to comply with
fair use and minimize storage footprint.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timedelta
from contextlib import contextmanager
import atexit
import threading
import time

from app.config import settings

logger = logging.getLogger(__name__)


class TemporaryStorage:
    """Manages temporary video storage with automatic cleanup."""

    def __init__(self, base_dir: Optional[Path] = None, cleanup_after_minutes: int = 60):
        """Initialize temporary storage manager.

        Args:
            base_dir: Base directory for temporary storage (defaults to downloads/temp)
            cleanup_after_minutes: Minutes before automatic cleanup (default 60)
        """
        self.base_dir = base_dir or (settings.download_dir / "temp")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cleanup_after_seconds = cleanup_after_minutes * 60
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()

        # Register cleanup on exit
        atexit.register(self.cleanup_all)

        logger.info(f"Temporary storage initialized: {self.base_dir}")

    def create_temp_dir(self, prefix: str = "video") -> Path:
        """Create a unique temporary directory.

        Args:
            prefix: Directory name prefix

        Returns:
            Path to created temporary directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_dir = self.base_dir / f"{prefix}_{timestamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir

    @contextmanager
    def temporary_video(self, video_path: Path, auto_cleanup: bool = True):
        """Context manager for temporary video file access.

        Usage:
            with temp_storage.temporary_video(video_path) as temp_path:
                # Use temp_path for analysis
                result = analyze_video(temp_path)
            # Video is automatically deleted after context exit

        Args:
            video_path: Path to video file
            auto_cleanup: Whether to delete video on context exit

        Yields:
            Path to temporary video file
        """
        temp_dir = self.create_temp_dir(prefix=f"analysis_{video_path.stem}")
        temp_video = temp_dir / video_path.name

        try:
            # Move video to temporary location (faster than copy)
            if video_path.exists():
                shutil.move(str(video_path), str(temp_video))
                logger.info(f"Moved video to temporary storage: {temp_video}")

            yield temp_video

        finally:
            if auto_cleanup and temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    logger.error(f"Failed to cleanup temporary directory {temp_dir}: {e}")

    def schedule_cleanup(self, file_path: Path, delay_seconds: Optional[int] = None):
        """Schedule automatic cleanup of a file after delay.

        Args:
            file_path: Path to file to cleanup
            delay_seconds: Seconds before cleanup (defaults to instance setting)
        """
        delay = delay_seconds or self.cleanup_after_seconds

        def cleanup_task():
            time.sleep(delay)
            if file_path.exists():
                try:
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                    else:
                        file_path.unlink()
                    logger.info(f"Scheduled cleanup completed: {file_path}")
                except Exception as e:
                    logger.error(f"Scheduled cleanup failed for {file_path}: {e}")

        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()
        logger.debug(f"Scheduled cleanup for {file_path} in {delay} seconds")

    def cleanup_old_files(self, max_age_minutes: Optional[int] = None):
        """Clean up temporary files older than specified age.

        Args:
            max_age_minutes: Maximum age in minutes (defaults to instance setting)
        """
        max_age = max_age_minutes or (self.cleanup_after_seconds / 60)
        cutoff_time = datetime.now() - timedelta(minutes=max_age)

        if not self.base_dir.exists():
            return

        cleaned_count = 0
        for item in self.base_dir.iterdir():
            try:
                # Check modification time
                mtime = datetime.fromtimestamp(item.stat().st_mtime)

                if mtime < cutoff_time:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

                    cleaned_count += 1
                    logger.debug(f"Cleaned up old temporary item: {item}")

            except Exception as e:
                logger.error(f"Failed to cleanup {item}: {e}")

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old temporary items")

    def cleanup_all(self):
        """Clean up all temporary storage."""
        if not self.base_dir.exists():
            return

        try:
            shutil.rmtree(self.base_dir)
            logger.info(f"Cleaned up all temporary storage: {self.base_dir}")
        except Exception as e:
            logger.error(f"Failed to cleanup all temporary storage: {e}")

    def start_background_cleanup(self, interval_minutes: int = 30):
        """Start background thread for periodic cleanup.

        Args:
            interval_minutes: Minutes between cleanup runs
        """
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            logger.warning("Background cleanup already running")
            return

        def cleanup_loop():
            while not self._stop_cleanup.wait(interval_minutes * 60):
                logger.debug("Running background cleanup...")
                self.cleanup_old_files()

        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info(f"Started background cleanup (interval: {interval_minutes} minutes)")

    def stop_background_cleanup(self):
        """Stop background cleanup thread."""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)
            logger.info("Stopped background cleanup")

    def get_storage_stats(self) -> dict:
        """Get temporary storage statistics.

        Returns:
            Dictionary with storage stats
        """
        if not self.base_dir.exists():
            return {
                "total_files": 0,
                "total_dirs": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
            }

        total_files = 0
        total_dirs = 0
        total_size = 0

        for item in self.base_dir.rglob("*"):
            if item.is_file():
                total_files += 1
                total_size += item.stat().st_size
            elif item.is_dir():
                total_dirs += 1

        return {
            "total_files": total_files,
            "total_dirs": total_dirs,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_dir": str(self.base_dir),
        }


# Global temporary storage instance
temp_storage = TemporaryStorage()
