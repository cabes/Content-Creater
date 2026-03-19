"""Fish-Speech TTS provider - open-source, good cost-performance ratio."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from .base import BaseTTSProvider, TTSRequest, TTSResponse

logger = structlog.get_logger()


class FishSpeechProvider(BaseTTSProvider):
    """Fish-Speech API adapter."""

    name = "fish_speech"

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs: Any):
        super().__init__(api_key, base_url or "https://api.fish.audio/v1", **kwargs)

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "text": request.text,
            "reference_id": request.voice_id or "default",
            "format": request.output_format,
            "streaming": False,
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/tts", json=payload, headers=headers
            )
            resp.raise_for_status()
            audio_data = resp.content

        return TTSResponse(
            audio_data=audio_data,
            format=request.output_format,
            metadata={"provider": "fish_speech", "voice_id": request.voice_id},
        )

    async def list_voices(self) -> list[dict[str, Any]]:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{self.base_url}/models", headers=headers)
            if resp.status_code == 200:
                return resp.json().get("models", [])
        return []
