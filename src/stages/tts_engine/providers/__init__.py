"""TTS provider factory."""
from __future__ import annotations

from typing import Any

from src.core.config import get_settings

from .base import BaseTTSProvider, TTSRequest, TTSResponse
from .minimax import MinimaxTTSProvider
from .fish_speech import FishSpeechProvider
from .volcengine import VolcengineTTSProvider
from .siliconflow import SiliconFlowTTSProvider

__all__ = ["BaseTTSProvider", "TTSRequest", "TTSResponse", "get_tts_provider"]

_PROVIDERS: dict[str, type[BaseTTSProvider]] = {
    "minimax": MinimaxTTSProvider,
    "fish_speech": FishSpeechProvider,
    "volcengine": VolcengineTTSProvider,
    "siliconflow": SiliconFlowTTSProvider,
}


def get_tts_provider(provider: str | None = None, **overrides: Any) -> BaseTTSProvider:
    """Factory: create a TTS provider instance."""
    settings = get_settings()
    provider = provider or settings.tts.provider

    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise ValueError(f"Unknown TTS provider: {provider}. Available: {list(_PROVIDERS)}")

    return cls(
        api_key=overrides.get("api_key", settings.tts.api_key),
        base_url=overrides.get("base_url", settings.tts.base_url),
        **{k: v for k, v in overrides.items() if k not in ("api_key", "base_url")},
    )
