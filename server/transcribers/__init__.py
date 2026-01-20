"""
Transcriber factory and exports.

Usage:
    from server.transcribers import create_transcriber, TranscriptionResult

    # Create Whisper transcriber (default)
    transcriber = create_transcriber("whisper")

    # Create Parakeet transcriber (faster)
    transcriber = create_transcriber("parakeet")

    # Transcribe
    result = transcriber.transcribe(audio_array)
"""

from .base import BaseTranscriber, TranscriptionResult

# Lazy imports to avoid loading heavy dependencies
_TRANSCRIBERS = {}


def _get_whisper_class():
    from .whisper import WhisperTranscriber
    return WhisperTranscriber


def _get_parakeet_class():
    from .parakeet import ParakeetTranscriber
    return ParakeetTranscriber


TRANSCRIBER_REGISTRY = {
    "whisper": _get_whisper_class,
    "parakeet": _get_parakeet_class,
}


def create_transcriber(
    engine: str = "whisper",
    **kwargs,
) -> BaseTranscriber:
    """
    Create a transcriber instance.

    Args:
        engine: Transcriber engine ("whisper" or "parakeet")
        **kwargs: Engine-specific configuration

    Returns:
        BaseTranscriber instance

    Raises:
        ValueError: If engine is not supported
        ImportError: If required dependencies are missing

    Example:
        # Whisper with custom model
        transcriber = create_transcriber("whisper", model_name="medium")

        # Parakeet (2x faster)
        transcriber = create_transcriber("parakeet")
    """
    if engine not in TRANSCRIBER_REGISTRY:
        available = ", ".join(TRANSCRIBER_REGISTRY.keys())
        raise ValueError(f"Unknown transcriber engine: {engine}. Available: {available}")

    transcriber_class = TRANSCRIBER_REGISTRY[engine]()
    return transcriber_class(**kwargs)


def list_engines() -> list[str]:
    """List available transcriber engines."""
    return list(TRANSCRIBER_REGISTRY.keys())


__all__ = [
    "BaseTranscriber",
    "TranscriptionResult",
    "create_transcriber",
    "list_engines",
]
