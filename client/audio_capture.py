"""
Audio capture using WASAPI loopback (Windows only).
Captures system audio output using PyAudioWPatch.
"""

import threading
import time
from typing import Callable
import numpy as np

try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIO = True
except ImportError:
    pyaudio = None
    HAS_PYAUDIO = False

# Optional: better resampling with scipy
try:
    from scipy import signal
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


def resample_audio(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample audio to target sample rate."""
    if orig_sr == target_sr:
        return audio

    if HAS_SCIPY:
        # High quality resampling
        gcd = np.gcd(orig_sr, target_sr)
        up = target_sr // gcd
        down = orig_sr // gcd
        return signal.resample_poly(audio, up, down)
    else:
        # Simple linear interpolation
        duration = len(audio) / orig_sr
        target_len = int(duration * target_sr)
        indices = np.linspace(0, len(audio) - 1, target_len)
        return np.interp(indices, np.arange(len(audio)), audio)


class AudioCapture:
    """Captures system audio using WASAPI loopback."""

    def __init__(
        self,
        on_audio: Callable[[bytes], None],
        device_name: str | None = None,
        target_sample_rate: int = 16000,
        chunk_duration: float = 0.5,
    ):
        """
        Args:
            on_audio: Callback with raw audio bytes (int16, mono, 16kHz)
            device_name: Specific device name or None for default
            target_sample_rate: Target sample rate for output (default 16kHz for Whisper)
            chunk_duration: Duration of each chunk in seconds
        """
        if not HAS_PYAUDIO:
            raise ImportError("pyaudiowpatch required: pip install pyaudiowpatch")

        self.on_audio = on_audio
        self.device_name = device_name
        self.target_sample_rate = target_sample_rate
        self.chunk_duration = chunk_duration

        self._running = False
        self._thread: threading.Thread | None = None
        self._pa: pyaudio.PyAudio | None = None

    def list_devices(self) -> list[str]:
        """List available loopback devices."""
        devices = []
        pa = pyaudio.PyAudio()
        try:
            # Get WASAPI host API
            wasapi_info = None
            for i in range(pa.get_host_api_count()):
                info = pa.get_host_api_info_by_index(i)
                if info["name"] == "Windows WASAPI":
                    wasapi_info = info
                    break

            if wasapi_info:
                for i in range(pa.get_device_count()):
                    dev = pa.get_device_info_by_index(i)
                    if dev["hostApi"] == wasapi_info["index"] and dev.get("isLoopbackDevice", False):
                        devices.append(dev["name"])
        finally:
            pa.terminate()
        return devices

    def _find_loopback_device(self, pa: pyaudio.PyAudio) -> dict | None:
        """Find the loopback device to use."""
        # Get WASAPI host API index
        wasapi_index = None
        for i in range(pa.get_host_api_count()):
            info = pa.get_host_api_info_by_index(i)
            if info["name"] == "Windows WASAPI":
                wasapi_index = info["index"]
                break

        if wasapi_index is None:
            print("Error: WASAPI not found")
            return None

        # Find loopback device
        for i in range(pa.get_device_count()):
            dev = pa.get_device_info_by_index(i)
            if dev["hostApi"] != wasapi_index:
                continue
            if not dev.get("isLoopbackDevice", False):
                continue

            # Match by name if specified
            if self.device_name:
                if self.device_name.lower() in dev["name"].lower():
                    return dev
            else:
                # Return first loopback device (default speakers)
                return dev

        return None

    def start(self):
        """Start capturing audio."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop capturing."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _capture_loop(self):
        """Main capture loop."""
        self._pa = pyaudio.PyAudio()

        try:
            device = self._find_loopback_device(self._pa)
            if device is None:
                print("Error: No loopback device found")
                if self.device_name:
                    print(f"  Requested: {self.device_name}")
                print("  Available devices:")
                for dev in self.list_devices():
                    print(f"    - {dev}")
                return

            device_index = device["index"]
            native_sr = int(device["defaultSampleRate"])
            channels = int(device["maxInputChannels"])

            print(f"Capturing from: {device['name']}")
            print(f"Using sample rate: {native_sr} Hz (resampling to {self.target_sample_rate} Hz)")

            chunk_samples = int(native_sr * self.chunk_duration)

            stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=native_sr,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=chunk_samples,
            )

            try:
                while self._running:
                    try:
                        # Read audio chunk
                        data = stream.read(chunk_samples, exception_on_overflow=False)

                        # Convert to numpy
                        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

                        # Convert to mono if stereo
                        if channels > 1:
                            audio = audio.reshape(-1, channels).mean(axis=1)

                        # Resample to target rate
                        if native_sr != self.target_sample_rate:
                            audio = resample_audio(audio, native_sr, self.target_sample_rate)

                        # Convert back to int16 bytes
                        audio_int16 = (audio * 32767).astype(np.int16)
                        audio_bytes = audio_int16.tobytes()

                        # Callback
                        self.on_audio(audio_bytes)

                    except Exception as e:
                        print(f"Audio capture error: {e}")
                        time.sleep(0.1)

            finally:
                stream.stop_stream()
                stream.close()

        finally:
            self._pa.terminate()
            self._pa = None
