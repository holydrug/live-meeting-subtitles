"""Local translation using NLLB model."""

import threading

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    import torch
except ImportError:
    AutoTokenizer = None
    torch = None

from .base import Translator, TranslationError


# NLLB language codes
NLLB_CODES = {
    "EN": "eng_Latn",
    "RU": "rus_Cyrl",
    "DE": "deu_Latn",
    "FR": "fra_Latn",
    "ES": "spa_Latn",
    "IT": "ita_Latn",
    "PT": "por_Latn",
    "JA": "jpn_Jpan",
    "ZH": "zho_Hans",
    "KO": "kor_Hang",
    "UK": "ukr_Cyrl",
    "PL": "pol_Latn",
}


class LocalTranslator(Translator):
    """Local translation using NLLB from HuggingFace."""

    def __init__(
        self,
        model_name: str = "facebook/nllb-200-distilled-600M",
        device: str | None = None,
    ):
        if AutoTokenizer is None:
            raise ImportError(
                "transformers required: pip install transformers sentencepiece torch"
            )

        self.model_name = model_name
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        self._model = None
        self._tokenizer = None
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return f"Local NLLB ({self.model_name.split('/')[-1]})"

    def _load(self):
        """Lazy load model."""
        if self._model is not None:
            return

        with self._lock:
            if self._model is not None:
                return

            print(f"Loading local translation model: {self.model_name}...")
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            self._model = self._model.to(self.device)
            self._model.eval()
            print(f"Model loaded on {self.device}")

    def translate(self, text: str, target_lang: str, source_lang: str | None = None) -> str:
        if not text.strip():
            return ""

        self._load()

        target_code = NLLB_CODES.get(target_lang.upper())
        source_code = NLLB_CODES.get(source_lang.upper()) if source_lang else "eng_Latn"

        if not target_code:
            raise TranslationError(f"Unsupported target language: {target_lang}")

        try:
            self._tokenizer.src_lang = source_code

            inputs = self._tokenizer(
                text, return_tensors="pt", padding=True, truncation=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                generated = self._model.generate(
                    **inputs,
                    forced_bos_token_id=self._tokenizer.lang_code_to_id[target_code],
                    max_length=256,
                    num_beams=4,
                    early_stopping=True,
                )

            translated = self._tokenizer.batch_decode(generated, skip_special_tokens=True)
            return translated[0] if translated else ""

        except Exception as e:
            raise TranslationError(f"Local translation error: {e}") from e

    def unload(self):
        """Free GPU memory."""
        with self._lock:
            if self._model is not None:
                del self._model
                del self._tokenizer
                self._model = None
                self._tokenizer = None
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
