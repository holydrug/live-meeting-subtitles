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

    RECONNECT_DELAY = 3  # seconds between reconnect attempts

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
        self._connected = False

    def set_overlay(self, overlay: OverlayWindow):
        self._overlay = overlay

    async def connect(self) -> bool:
        """Connect to the server."""
        uri = f"ws://{self.host}:{self.port}"

        if self._overlay:
            self._overlay.set_status(f"Connecting to {self.host}:{self.port}...")

        try:
            self._ws = await websockets.connect(uri)
            print("Connected!")
            self._connected = True
            if self._overlay:
                self._overlay.set_status("Connected - Listening...")
            return True
        except Exception as e:
            self._connected = False
            if self._overlay:
                self._overlay.set_status(f"Waiting for server...")
            return False

    async def _connect_with_retry(self) -> bool:
        """Keep trying to connect until successful or stopped."""
        uri = f"ws://{self.host}:{self.port}"
        print(f"Connecting to {uri}...")

        attempt = 0
        while self._running:
            attempt += 1
            if await self.connect():
                return True

            print(f"Reconnect attempt {attempt} failed, retrying in {self.RECONNECT_DELAY}s...")
            if self._overlay:
                self._overlay.set_status(f"Waiting for server... (attempt {attempt})")

            await asyncio.sleep(self.RECONNECT_DELAY)

        return False

    async def _send_audio(self, audio_bytes: bytes):
        """Send audio to server."""
        if self._ws and self._running and self._connected:
            try:
                await self._ws.send(audio_bytes)
            except Exception as e:
                # Connection lost
                self._connected = False

    def _on_audio(self, audio_bytes: bytes):
        """Callback from audio capture (runs in audio thread)."""
        if self._loop and self._running and self._connected and not self._loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(
                    self._send_audio(audio_bytes),
                    self._loop
                )
            except RuntimeError:
                # Event loop closed
                pass

    async def _receive_loop(self):
        """Receive results from server. Returns True if should reconnect."""
        try:
            async for message in self._ws:
                if not self._running:
                    return False

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

            # WebSocket closed normally
            print("\nServer closed connection")
            self._connected = False
            if self._overlay:
                self._overlay.set_status("Server stopped, reconnecting...")
            return True  # Should reconnect

        except websockets.exceptions.ConnectionClosed as e:
            print(f"\nConnection lost: {e}")
            self._connected = False
            if self._overlay:
                self._overlay.set_status("Connection lost, reconnecting...")
            return True  # Should reconnect

        except Exception as e:
            print(f"\nReceive error: {e}")
            self._connected = False
            if self._overlay:
                self._overlay.set_status(f"Error: {e}")
            return True  # Should reconnect

    async def run(self):
        """Main async loop with auto-reconnect."""
        self._loop = asyncio.get_event_loop()
        self._running = True

        # Start audio capture (runs independently)
        self._audio_capture = AudioCapture(
            on_audio=self._on_audio,
            device_name=self.device,
        )
        self._audio_capture.start()

        # Main connection loop with auto-reconnect
        while self._running:
            # Try to connect
            if not await self._connect_with_retry():
                print("Stopped during connection attempt")
                break  # Stopped while connecting

            # Receive loop (returns True if should reconnect)
            should_reconnect = await self._receive_loop()
            print(f"Receive loop ended, should_reconnect={should_reconnect}, running={self._running}")

            if not should_reconnect or not self._running:
                break

            # Close old websocket
            if self._ws:
                try:
                    await self._ws.close()
                except Exception:
                    pass
                self._ws = None

            print("Reconnecting in 1s...")
            await asyncio.sleep(1)

        # Cleanup
        if self._audio_capture:
            self._audio_capture.stop()

    def stop(self):
        """Stop the client."""
        self._running = False
        self._connected = False

        if self._audio_capture:
            self._audio_capture.stop()

        if self._ws:
            try:
                asyncio.run_coroutine_threadsafe(self._ws.close(), self._loop)
            except Exception:
                pass


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
        import signal

        app = QApplication(sys.argv)

        # Allow Ctrl+C to work
        signal.signal(signal.SIGINT, signal.SIG_DFL)

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
