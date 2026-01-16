"""DeepL API translator."""

import os

try:
    import deepl
except ImportError:
    deepl = None

from .base import Translator, TranslationError


class DeepLTranslator(Translator):
    """Translation using DeepL API."""

    def __init__(self, api_key: str | None = None):
        if deepl is None:
            raise ImportError("deepl library required: pip install deepl")

        self.api_key = api_key or os.environ.get("DEEPL_API_KEY")
        if not self.api_key:
            raise TranslationError(
                "DeepL API key required. Set DEEPL_API_KEY env var or pass api_key parameter."
            )

        self._client = deepl.Translator(self.api_key)

    @property
    def name(self) -> str:
        return "DeepL"

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if not text.strip():
            return ""

        try:
            result = self._client.translate_text(
                text,
                target_lang=target_lang.upper(),
                source_lang=source_lang.upper() if source_lang else None,
            )
            return result.text
        except deepl.DeepLException as e:
            raise TranslationError(f"DeepL error: {e}") from e
