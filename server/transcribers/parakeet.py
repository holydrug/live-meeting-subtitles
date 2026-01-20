"""
Parakeet TDT v3 transcriber using NVIDIA NeMo.
Optimized for high-speed transcription on NVIDIA GPUs.

Note: Requires PyTorch nightly with CUDA 12.8 for RTX 5090 support.
"""

import time
import tempfile
import os
import numpy as np
import scipy.io.wavfile as wav

from .base import BaseTranscriber, TranscriptionResult

try:
    import nemo.collections.asr as nemo_asr
    from omegaconf import open_dict
    NEMO_AVAILABLE = True
except ImportError:
    NEMO_AVAILABLE = False


class ParakeetTranscriber(BaseTranscriber):
    """
    Parakeet TDT v3 transcription using NVIDIA NeMo.

    Parakeet is ~2x faster than Whisper with similar quality.
    Supports 25 European languages including English and Russian.
    Built-in punctuation and capitalization.
    """

    def __init__(
        self,
        model_name: str = "nvidia/parakeet-tdt-0.6b-v3",
        device: str = "cuda",
        language: str | None = None,  # Auto-detect by default
    ):
        if not NEMO_AVAILABLE:
            raise ImportError(
                "NeMo toolkit required: pip install nemo_toolkit[asr]\n"
                "For RTX 5090: pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128"
            )

        self.model_name = model_name
        self.device = device
        self.language = language
        self._model = None
        self._temp_dir = tempfile.mkdtemp(prefix="parakeet_")

    def load(self) -> None:
        """Load the model (call once at startup)."""
        if self._model is not None:
            return

        print(f"Loading Parakeet model: {self.model_name} on {self.device}...")
        start = time.time()

        self._model = nemo_asr.models.ASRModel.from_pretrained(self.model_name)

        # Disable CUDA graphs (workaround for PyTorch nightly compatibility)
        self._disable_cuda_graphs()

        print(f"Parakeet model loaded in {time.time() - start:.1f}s")

    def _disable_cuda_graphs(self) -> None:
        """Disable CUDA graphs for PyTorch nightly compatibility."""
        if self._model is None:
            return

        try:
            decoding_cfg = self._model.cfg.decoding.copy()
            with open_dict(decoding_cfg):
                decoding_cfg.greedy.use_cuda_graph_decoder = False
                decoding_cfg.greedy.loop_labels = False
            self._model.change_decoding_strategy(decoding_cfg)
        except Exception as e:
            print(f"Warning: Could not disable CUDA graphs: {e}")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> TranscriptionResult | None:
        """
        Transcribe audio chunk.

        Args:
            audio: Float32 numpy array, mono, normalized to [-1, 1]
            sample_rate: Sample rate (should be 16000 for Parakeet)

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

        # NeMo requires file path, so write temp file
        temp_path = os.path.join(self._temp_dir, "temp_audio.wav")
        audio_int16 = (audio * 32767).astype(np.int16)
        wav.write(temp_path, sample_rate, audio_int16)

        try:
            # Transcribe
            results = self._model.transcribe([temp_path])

            if not results or not results[0].text:
                return None

            result = results[0]
            text = result.text.strip()

            if not text:
                return None

            # Parakeet auto-detects language
            detected_lang = getattr(result, 'lang', 'unknown')
            if detected_lang == 'unknown' and self.language:
                detected_lang = self.language

            return TranscriptionResult(
                text=text,
                language=detected_lang,
                confidence=1.0,  # Parakeet doesn't provide confidence
                processing_time=time.time() - start,
            )

        except Exception as e:
            print(f"Parakeet transcription error: {e}")
            return None

        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

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

        # Cleanup temp directory
        try:
            import shutil
            if os.path.exists(self._temp_dir):
                shutil.rmtree(self._temp_dir)
        except Exception:
            pass

    def is_loaded(self) -> bool:
        return self._model is not None
