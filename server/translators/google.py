"""Google Translate (free, unofficial)."""

try:
    from googletrans import Translator as GoogleTransAPI
except ImportError:
    GoogleTransAPI = None

from .base import Translator, TranslationError


# Language code mapping (our codes -> googletrans codes)
LANG_MAP = {
    "EN": "en",
    "RU": "ru",
    "DE": "de",
    "FR": "fr",
    "ES": "es",
    "IT": "it",
    "PT": "pt",
    "JA": "ja",
    "ZH": "zh-cn",
    "KO": "ko",
    "UK": "uk",
    "PL": "pl",
}


class GoogleTranslator(Translator):
    """Free Google Translate using googletrans library."""

    def __init__(self):
        if GoogleTransAPI is None:
            raise ImportError("googletrans required: pip install googletrans==4.0.0rc1")

        self._client = GoogleTransAPI()

    @property
    def name(self) -> str:
        return "Google Translate"

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if not text.strip():
            return ""

        # Map language codes
        dest = LANG_MAP.get(target_lang.upper(), target_lang.lower())
        src = LANG_MAP.get(source_lang.upper(), source_lang.lower()) if source_lang else "auto"

        try:
            result = self._client.translate(text, dest=dest, src=src)
            return result.text
        except Exception as e:
            raise TranslationError(f"Google Translate error: {e}") from e
