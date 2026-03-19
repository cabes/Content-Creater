"""Abstract base class for TTS providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TTSRequest:
    """Request to synthesize speech."""
    text: str
    voice_id: str = ""
    speed: float = 1.0
    pitch: float = 0.0  # semitones adjustment
    volume: float = 1.0
    emotion: str = ""
    ssml: str = ""  # If provided, use SSML instead of plain text
    output_format: str = "mp3"
    sample_rate: int = 44100


@dataclass
class TTSResponse:
    """Response from TTS synthesis."""
    audio_data: bytes = b""
    duration: float = 0.0
    sample_rate: int = 44100
    format: str = "mp3"
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTTSProvider(ABC):
    """Abstract base for TTS providers."""

    name: str = "base"

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs: Any):
        self.api_key = api_key
        self.base_url = base_url
        self.extra = kwargs

    @abstractmethod
    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """Synthesize speech from text or SSML."""
        ...

    @abstractmethod
    async def list_voices(self) -> list[dict[str, Any]]:
        """List available voices."""
        ...

    async def clone_voice(self, name: str, audio_data: bytes) -> str:
        """Clone a voice from audio sample. Returns voice_id."""
        raise NotImplementedError(f"{self.name} does not support voice cloning")
