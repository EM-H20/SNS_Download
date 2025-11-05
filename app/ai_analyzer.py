"""AI-powered video analysis module.

Extracts text descriptions, transcripts, and metadata from video content
using AI models. Designed for transformative fair use AI analysis.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class VideoAnalysisResult:
    """Result of AI video analysis."""

    def __init__(
        self,
        video_path: Path,
        transcript: Optional[str] = None,
        description: Optional[str] = None,
        summary: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        detected_objects: Optional[List[str]] = None,
        detected_text: Optional[List[str]] = None,
        sentiment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Initialize analysis result.

        Args:
            video_path: Path to analyzed video
            transcript: Speech-to-text transcript
            description: AI-generated description
            summary: Brief summary of content
            keywords: Extracted keywords/topics
            detected_objects: Visual objects detected
            detected_text: OCR text from video
            sentiment: Sentiment analysis result
            metadata: Additional metadata
        """
        self.video_path = video_path
        self.transcript = transcript
        self.description = description
        self.summary = summary
        self.keywords = keywords or []
        self.detected_objects = detected_objects or []
        self.detected_text = detected_text or []
        self.sentiment = sentiment
        self.metadata = metadata or {}
        self.analyzed_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "video_path": str(self.video_path),
            "transcript": self.transcript,
            "description": self.description,
            "summary": self.summary,
            "keywords": self.keywords,
            "detected_objects": self.detected_objects,
            "detected_text": self.detected_text,
            "sentiment": self.sentiment,
            "metadata": self.metadata,
            "analyzed_at": self.analyzed_at.isoformat(),
        }

    def to_text(self) -> str:
        """Convert analysis to plain text format."""
        lines = [
            f"Video Analysis: {self.video_path.name}",
            f"Analyzed: {self.analyzed_at.isoformat()}",
            "",
        ]

        if self.summary:
            lines.extend(["Summary:", self.summary, ""])

        if self.description:
            lines.extend(["Description:", self.description, ""])

        if self.transcript:
            lines.extend(["Transcript:", self.transcript, ""])

        if self.keywords:
            lines.extend(["Keywords:", ", ".join(self.keywords), ""])

        if self.detected_objects:
            lines.extend(["Detected Objects:", ", ".join(self.detected_objects), ""])

        if self.detected_text:
            lines.extend(["Detected Text:", ", ".join(self.detected_text), ""])

        if self.sentiment:
            lines.extend(["Sentiment:", self.sentiment, ""])

        return "\n".join(lines)


class BaseVideoAnalyzer(ABC):
    """Abstract base class for video analyzers."""

    @abstractmethod
    def analyze(self, video_path: Path) -> VideoAnalysisResult:
        """Analyze video and extract information.

        Args:
            video_path: Path to video file

        Returns:
            Analysis result with extracted information

        Raises:
            Exception: If analysis fails
        """
        pass


class MockVideoAnalyzer(BaseVideoAnalyzer):
    """Mock analyzer for testing and development.

    Replace with actual AI service implementation (OpenAI, Claude, etc.)
    """

    def analyze(self, video_path: Path) -> VideoAnalysisResult:
        """Mock analysis - returns placeholder data.

        Args:
            video_path: Path to video file

        Returns:
            Mock analysis result
        """
        logger.warning(
            f"Using MockVideoAnalyzer - replace with actual AI service. Video: {video_path}"
        )

        # Get basic file info
        file_size = video_path.stat().st_size
        file_name = video_path.name

        return VideoAnalysisResult(
            video_path=video_path,
            summary=f"[MOCK] This is a placeholder analysis for {file_name}",
            description=(
                f"[MOCK] Video file analysis placeholder. "
                f"File size: {file_size:,} bytes. "
                "Replace MockVideoAnalyzer with actual AI service (OpenAI Vision, Claude, etc.)"
            ),
            keywords=["mock", "placeholder", "demo"],
            metadata={
                "analyzer": "MockVideoAnalyzer",
                "file_size_bytes": file_size,
                "note": "Replace with actual AI service",
            },
        )


class OpenAIVideoAnalyzer(BaseVideoAnalyzer):
    """OpenAI-based video analyzer (placeholder implementation).

    Requires:
        pip install openai
    """

    def __init__(self, api_key: str):
        """Initialize OpenAI analyzer.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        # TODO: Initialize OpenAI client
        logger.info("OpenAI video analyzer initialized (placeholder)")

    def analyze(self, video_path: Path) -> VideoAnalysisResult:
        """Analyze video using OpenAI.

        Args:
            video_path: Path to video file

        Returns:
            Analysis result

        Raises:
            NotImplementedError: Not yet implemented
        """
        raise NotImplementedError(
            "OpenAI video analysis not yet implemented. "
            "Implement using OpenAI Vision API or Whisper for transcription."
        )


class VideoAnalyzer:
    """Main video analyzer with multiple backend support."""

    def __init__(self, analyzer: Optional[BaseVideoAnalyzer] = None):
        """Initialize video analyzer.

        Args:
            analyzer: Specific analyzer implementation (defaults to MockVideoAnalyzer)
        """
        self.analyzer = analyzer or MockVideoAnalyzer()

    def analyze_video(
        self,
        video_path: Path,
        save_result: bool = True,
        output_format: str = "json",
    ) -> VideoAnalysisResult:
        """Analyze video and optionally save result.

        Args:
            video_path: Path to video file
            save_result: Whether to save analysis result to file
            output_format: Output format ('json' or 'text')

        Returns:
            Video analysis result

        Raises:
            FileNotFoundError: If video doesn't exist
            Exception: If analysis fails
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        logger.info(f"Analyzing video: {video_path}")
        result = self.analyzer.analyze(video_path)

        if save_result:
            self._save_result(result, output_format)

        return result

    def _save_result(self, result: VideoAnalysisResult, output_format: str):
        """Save analysis result to file.

        Args:
            result: Analysis result
            output_format: Output format ('json' or 'text')
        """
        import json

        output_dir = result.video_path.parent
        base_name = result.video_path.stem

        if output_format == "json":
            output_file = output_dir / f"{base_name}_analysis.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        else:  # text
            output_file = output_dir / f"{base_name}_analysis.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.to_text())

        logger.info(f"Saved analysis result: {output_file}")


# Global analyzer instance (using mock by default)
video_analyzer = VideoAnalyzer()


def analyze_and_cleanup(video_path: Path) -> VideoAnalysisResult:
    """Convenience function: analyze video then delete it.

    This is the main function for the AI analysis workflow:
    1. Download video (temporary)
    2. Analyze with AI
    3. Delete video
    4. Return text analysis

    Args:
        video_path: Path to temporary video file

    Returns:
        Analysis result (video will be deleted)

    Raises:
        FileNotFoundError: If video doesn't exist
        Exception: If analysis fails
    """
    from app.temp_storage import temp_storage

    # Analyze video
    result = video_analyzer.analyze_video(video_path, save_result=True)

    # Delete video using temp storage context manager
    if video_path.exists():
        video_path.unlink()
        logger.info(f"Deleted video after analysis: {video_path}")

    return result
