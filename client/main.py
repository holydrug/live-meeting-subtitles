"""
Windows client for voice transcription.
Captures audio and sends to WSL server, displays results in overlay.
"""

import sys
import asyncio
import argparse
import threading
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import websockets
except ImportError:
    websockets = None

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from shared.protocol import DEFAULT_HOST, DEFAULT_PORT, MessageType, decode_message
from client.audio_capture import AudioCapture
from client.overlay import OverlayWindow


class VoiceClient:
    """WebSocket client that captures audio and displays results."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        device: str | None = None,
    ):
        if websockets is None:
            raise ImportError("websockets required: pip install websockets")

        self.host = host
        self.port = port
        self.device = device

        self._ws = None
        self._audio_capture: AudioCapture | None = None
        self._overlay: OverlayWindow | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._running = False

    def set_overlay(self, overlay: OverlayWindow):
        self._overlay = overlay

    async def connect(self):
        """Connect to the server."""
        uri = f"ws://{self.host}:{self.port}"
        print(f"Connecting to {uri}...")

        if self._overlay:
            self._overlay.set_status(f"Connecting to {self.host}:{self.port}...")

        try:
            self._ws = await websockets.connect(uri)
            print("Connected!")
            if self._overlay:
                self._overlay.set_status("Connected - Listening...")
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            if self._overlay:
                self._overlay.set_status(f"Connection failed: {e}")
            return False

    async def _send_audio(self, audio_bytes: bytes):
        """Send audio to server."""
        if self._ws and self._running:
            try:
                await self._ws.send(audio_bytes)
            except Exception as e:
                print(f"Send error: {e}")

    def _on_audio(self, audio_bytes: bytes):
        """Callback from audio capture (runs in audio thread)."""
        if self._loop and self._running:
            asyncio.run_coroutine_threadsafe(
                self._send_audio(audio_bytes),
                self._loop
            )

    async def _receive_loop(self):
        """Receive results from server."""
        try:
            async for message in self._ws:
                if not self._running:
                    break

                data = decode_message(message)
                msg_type = data.get("type")

                if msg_type == MessageType.RESULT:
                    original = data.get("original", "")
                    translated = data.get("translated", "")

                    if original and self._overlay:
                        self._overlay.add_text(original, translated)

                    # Also print to console
                    print(f"\n[EN] {original}")
                    if translated:
                        print(f"[RU] {translated}")

                elif msg_type == MessageType.STATUS:
                    status = data.get("message", "")
                    if self._overlay:
                        self._overlay.set_status(status)

                elif msg_type == MessageType.ERROR:
                    error = data.get("message", "Unknown error")
                    print(f"Server error: {error}")

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            if self._overlay:
                self._overlay.set_status("Disconnected")

    async def run(self):
        """Main async loop."""
        self._loop = asyncio.get_event_loop()
        self._running = True

        if not await self.connect():
            return

        # Start audio capture
        self._audio_capture = AudioCapture(
            on_audio=self._on_audio,
            device_name=self.device,
        )
        self._audio_capture.start()

        # Receive loop
        await self._receive_loop()

    def stop(self):
        """Stop the client."""
        self._running = False

        if self._audio_capture:
            self._audio_capture.stop()

        if self._ws:
            asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)


def run_async_client(client: VoiceClient):
    """Run async client in a thread."""
    asyncio.run(client.run())


def main():
    parser = argparse.ArgumentParser(description="Voice Analyzer Client")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Server host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server port")
    parser.add_argument("--device", help="Audio device name (partial match)")
    parser.add_argument("--list-devices", action="store_true", help="List audio devices")
    parser.add_argument("--no-overlay", action="store_true", help="Console only mode")

    args = parser.parse_args()

    # List devices
    if args.list_devices:
        from client.audio_capture import AudioCapture
        ac = AudioCapture(lambda x: None)
        print("Available loopback devices:")
        for dev in ac.list_devices():
            print(f"  - {dev}")
        return

    # Create client
    client = VoiceClient(
        host=args.host,
        port=args.port,
        device=args.device,
    )

    if args.no_overlay:
        # Console only
        print("Running in console mode. Press Ctrl+C to stop.")
        try:
            asyncio.run(client.run())
        except KeyboardInterrupt:
            client.stop()
    else:
        # GUI mode
        app = QApplication(sys.argv)

        overlay = OverlayWindow()
        client.set_overlay(overlay)
        overlay.show()

        # Run async client in background thread
        client_thread = threading.Thread(target=run_async_client, args=(client,), daemon=True)
        client_thread.start()

        # Handle close
        def on_close():
            client.stop()

        overlay.destroyed.connect(on_close)

        # Run Qt
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
