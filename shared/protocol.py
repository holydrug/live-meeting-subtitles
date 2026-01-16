"""
Communication protocol between Windows client and WSL server.
Uses WebSocket for bidirectional communication.
"""

import json
from dataclasses import dataclass, asdict
from typing import Literal
from enum import Enum


# Default connection settings
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876


class MessageType(str, Enum):
    # Client -> Server
    AUDIO_CHUNK = "audio_chunk"      # Raw audio data
    SET_CONFIG = "set_config"        # Update settings
    PING = "ping"

    # Server -> Client
    TRANSCRIPTION = "transcription"  # Transcribed text
    TRANSLATION = "translation"      # Translated text
    RESULT = "result"                # Combined result
    ERROR = "error"
    PONG = "pong"
    STATUS = "status"                # Server status update


@dataclass
class AudioChunkMessage:
    """Audio data from client to server."""
    type: str = MessageType.AUDIO_CHUNK
    sample_rate: int = 16000
    channels: int = 1
    # audio_data is sent as binary frame, not in JSON


@dataclass
class TranscriptionResult:
    """Result from server to client."""
    original: str           # Original transcribed text
    translated: str         # Translated text (may be empty)
    language: str           # Detected language
    confidence: float       # Language detection confidence
    timestamp: float        # Server timestamp
    type: str = MessageType.RESULT


@dataclass
class StatusMessage:
    """Server status update."""
    status: Literal["ready", "processing", "error"]
    message: str = ""
    model_loaded: bool = False
    type: str = MessageType.STATUS


@dataclass
class ConfigMessage:
    """Configuration update."""
    type: str = MessageType.SET_CONFIG
    translation_provider: str | None = None  # deepl, google, local, none
    target_language: str | None = None       # RU, DE, etc.
    source_language: str | None = None       # EN, auto, etc.


def encode_message(msg: dict | object) -> str:
    """Encode message to JSON string."""
    if hasattr(msg, '__dataclass_fields__'):
        return json.dumps(asdict(msg))
    return json.dumps(msg)


def decode_message(data: str) -> dict:
    """Decode JSON string to dict."""
    return json.loads(data)
