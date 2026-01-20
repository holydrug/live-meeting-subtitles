"""
Whisper transcriber using faster-whisper.
Optimized for real-time streaming with CUDA.
"""

import time
import numpy as np

from .base import BaseTranscriber, TranscriptionResult

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


class WhisperTranscriber(BaseTranscriber):
    """Whisper transcription using faster-whisper."""

    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16",
        language: str | None = "en",
    ):
        if WhisperModel is None:
            raise ImportError("faster-whisper required: pip install faster-whisper")

        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self._model: WhisperModel | None = None

    def load(self) -> None:
        """Load the model (call once at startup)."""
        if self._model is not None:
            return

        print(f"Loading Whisper model: {self.model_name} on {self.device}...")
        start = time.time()
        self._model = WhisperModel(
            self.model_name,
            device=self.device,
            compute_type=self.compute_type,
        )
        print(f"Whisper model loaded in {time.time() - start:.1f}s")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult | None:
        """
        Transcribe audio chunk.

        Args:
            audio: Float32 numpy array, mono, normalized to [-1, 1]
            sample_rate: Sample rate (should be 16000 for Whisper)

        Returns:
            TranscriptionResult or None if no speech detected
        """
        if self._model is None:
            self.load()

        # Skip if too quiet
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 0.005:
            return None

        start = time.time()

        segments, info = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        # Collect all text
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        if not text_parts:
            return None

        return TranscriptionResult(
            text=" ".join(text_parts),
            language=info.language,
            confidence=info.language_probability,
            processing_time=time.time() - start,
        )

    def unload(self) -> None:
        """Unload model to free GPU memory."""
        if self._model is not None:
            del self._model
            self._model = None
            try:
                import torch
                torch.cuda.empty_cache()
            except ImportError:
                pass

    def is_loaded(self) -> bool:
        return self._model is not None
