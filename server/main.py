"""
WebSocket server for voice transcription and translation.
Runs in WSL with CUDA support.
"""

import asyncio
import json
import time
import argparse
import numpy as np

try:
    import websockets
except ImportError:
    websockets = None

import sys
sys.path.insert(0, str(__file__).rsplit("/", 2)[0])

from shared.protocol import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    MessageType,
    TranscriptionResult,
    StatusMessage,
    encode_message,
    decode_message,
)
from server.transcriber import Transcriber
from server.translators import create_translator, Translator


class TranscriptionServer:
    """WebSocket server for real-time transcription."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        model: str = "large-v3",
        device: str = "cuda",
        translation_provider: str = "google",
        target_language: str = "RU",
        source_language: str = "en",
    ):
        if websockets is None:
            raise ImportError("websockets required: pip install websockets")

        self.host = host
        self.port = port
        self.target_language = target_language
        self.source_language = source_language

        # Initialize transcriber
        self.transcriber = Transcriber(
            model_name=model,
            device=device,
            language=source_language,
        )

        # Initialize translator
        self.translator: Translator | None = None
        self.translation_provider = translation_provider
        if translation_provider and translation_provider != "none":
            try:
                self.translator = create_translator(translation_provider)
                print(f"Translator: {self.translator.name}")
            except Exception as e:
                print(f"Warning: Could not initialize translator: {e}")

        # Audio buffer for accumulating chunks
        self._audio_buffer: list[np.ndarray] = []
        self._buffer_duration = 0.0
        self._sample_rate = 16000
        self._min_duration = 2.0  # Minimum seconds before processing
        self._max_duration = 10.0  # Maximum seconds before forced processing

        self._clients: set = set()

    async def start(self):
        """Start the WebSocket server."""
        # Load model before accepting connections
        print("Loading transcription model...")
        self.transcriber.load()

        print(f"Starting server on ws://{self.host}:{self.port}")
        async with websockets.serve(self._handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def _handle_client(self, websocket):
        """Handle a client connection."""
        self._clients.add(websocket)
        client_id = id(websocket)
        print(f"Client connected: {client_id}")

        # Send ready status
        await websocket.send(encode_message({
            "type": MessageType.STATUS,
            "status": "ready",
            "message": "Server ready",
            "model_loaded": True,
        }))

        try:
            async for message in websocket:
                if isinstance(message, bytes):
                    # Binary message = audio data
                    await self._handle_audio(websocket, message)
                else:
                    # Text message = JSON command
                    await self._handle_command(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            print(f"Client disconnected: {client_id}")

    async def _handle_audio(self, websocket, data: bytes):
        """Handle incoming audio chunk."""
        # Convert bytes to float32 numpy array
        # Expecting: int16, mono, 16kHz
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0

        # Add to buffer
        self._audio_buffer.append(audio)
        self._buffer_duration += len(audio) / self._sample_rate

        # Check if we should process
        should_process = self._buffer_duration >= self._min_duration and (
            self._buffer_duration >= self._max_duration or
            self._is_silence(audio)
        )

        if should_process:
            await self._process_buffer(websocket)

    def _is_silence(self, audio: np.ndarray, threshold: float = 0.01) -> bool:
        """Check if audio chunk ends with silence."""
        check_samples = min(len(audio), 4000)  # Last 0.25s
        rms = np.sqrt(np.mean(audio[-check_samples:] ** 2))
        return rms < threshold

    async def _process_buffer(self, websocket):
        """Process accumulated audio buffer."""
        if not self._audio_buffer:
            return

        # Get buffered audio
        full_audio = np.concatenate(self._audio_buffer)
        self._audio_buffer = []
        self._buffer_duration = 0.0

        # Transcribe (run in thread to not block)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.transcriber.transcribe,
            full_audio,
            self._sample_rate,
        )

        if result is None:
            return

        # Translate
        translated = ""
        if self.translator and result.text:
            try:
                translated = await loop.run_in_executor(
                    None,
                    self.translator.translate,
                    result.text,
                    self.target_language,
                    result.language,
                )
            except Exception as e:
                print(f"Translation error: {e}")

        # Send result
        response = {
            "type": MessageType.RESULT,
            "original": result.text,
            "translated": translated,
            "language": result.language,
            "confidence": result.confidence,
            "timestamp": time.time(),
        }

        await websocket.send(encode_message(response))

        # Also print to server console
        print(f"\n[{result.language}] {result.text}")
        if translated:
            print(f"[{self.target_language}] {translated}")

    async def _handle_command(self, websocket, message: str):
        """Handle JSON command."""
        try:
            data = decode_message(message)
            msg_type = data.get("type")

            if msg_type == MessageType.PING:
                await websocket.send(encode_message({"type": MessageType.PONG}))

            elif msg_type == MessageType.SET_CONFIG:
                # Update configuration
                if "translation_provider" in data:
                    provider = data["translation_provider"]
                    if provider != self.translation_provider:
                        try:
                            self.translator = create_translator(provider) if provider else None
                            self.translation_provider = provider
                            print(f"Switched translator to: {provider}")
                        except Exception as e:
                            await websocket.send(encode_message({
                                "type": MessageType.ERROR,
                                "message": f"Failed to switch translator: {e}",
                            }))

                if "target_language" in data:
                    self.target_language = data["target_language"]

                if "source_language" in data:
                    self.source_language = data["source_language"]

        except json.JSONDecodeError as e:
            await websocket.send(encode_message({
                "type": MessageType.ERROR,
                "message": f"Invalid JSON: {e}",
            }))


def main():
    parser = argparse.ArgumentParser(description="Voice Transcription Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to bind to")
    parser.add_argument("--model", default="large-v3", help="Whisper model name")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--translator", default="google",
                        choices=["deepl", "google", "local", "none"])
    parser.add_argument("--target-lang", default="RU", help="Target language for translation")
    parser.add_argument("--source-lang", default="en", help="Source language (or 'auto')")

    args = parser.parse_args()

    server = TranscriptionServer(
        host=args.host,
        port=args.port,
        model=args.model,
        device=args.device,
        translation_provider=args.translator if args.translator != "none" else None,
        target_language=args.target_lang,
        source_language=args.source_lang if args.source_lang != "auto" else None,
    )

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
