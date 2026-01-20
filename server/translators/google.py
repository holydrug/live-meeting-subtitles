"""Google Translate (free, using deep-translator)."""

try:
    from deep_translator import GoogleTranslator as DeepGoogleTranslator
except ImportError:
    DeepGoogleTranslator = None

from .base import Translator, TranslationError


# Language code mapping (our codes -> google codes)
LANG_MAP = {
    "EN": "en",
    "RU": "ru",
    "DE": "de",
    "FR": "fr",
    "ES": "es",
    "IT": "it",
    "PT": "pt",
    "JA": "ja",
    "ZH": "zh-CN",
    "KO": "ko",
    "UK": "uk",
    "PL": "pl",
}


class GoogleTranslator(Translator):
    """Free Google Translate using deep-translator library."""

    def __init__(self):
        if DeepGoogleTranslator is None:
            raise ImportError("deep-translator required: pip install deep-translator")

    @property
    def name(self) -> str:
        return "Google Translate"

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if not text.strip():
            return ""

        # Map language codes
        target = LANG_MAP.get(target_lang.upper(), target_lang.lower())
        source = LANG_MAP.get(source_lang.upper(), source_lang.lower()) if source_lang else "auto"

        try:
            translator = DeepGoogleTranslator(source=source, target=target)
            return translator.translate(text)
        except Exception as e:
            raise TranslationError(f"Google Translate error: {e}") from e
