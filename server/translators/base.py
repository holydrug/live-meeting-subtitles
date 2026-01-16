"""Base translator interface."""

from abc import ABC, abstractmethod


class TranslationError(Exception):
    """Translation failed."""
    pass


class Translator(ABC):
    """Abstract base class for translators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the translator."""
        pass

    @abstractmethod
    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        """
        Translate text.

        Args:
            text: Text to translate
            target_lang: Target language code (e.g., "RU", "DE")
            source_lang: Source language code or None for auto-detect

        Returns:
            Translated text

        Raises:
            TranslationError: If translation fails
        """
        pass
