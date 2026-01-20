"""
Base transcriber interface.
All transcriber implementations must inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""
    text: str
    language: str
    confidence: float
    processing_time: float


class BaseTranscriber(ABC):
    """Abstract base class for all transcribers."""

    @abstractmethod
    def load(self) -> None:
        """Load the model into memory. Call once at startup."""
        pass

    @abstractmethod
    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult | None:
        """
        Transcribe audio chunk.

        Args:
            audio: Float32 numpy array, mono, normalized to [-1, 1]
            sample_rate: Sample rate (default 16000 Hz)

        Returns:
            TranscriptionResult or None if no speech detected
        """
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unload model to free GPU memory."""
        pass

    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return False
