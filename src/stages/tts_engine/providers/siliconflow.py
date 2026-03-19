"""SiliconFlow TTS provider - uses CosyVoice2/IndexTTS via OpenAI-compatible API."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from .base import BaseTTSProvider, TTSRequest, TTSResponse

logger = structlog.get_logger()

# Available voices on SiliconFlow CosyVoice2
SILICONFLOW_VOICES = {
    # CosyVoice2 preset voices
    "alex": "FunAudioLLM/CosyVoice2-0.5B:alex",
    "benjamin": "FunAudioLLM/CosyVoice2-0.5B:benjamin",
    "charles": "FunAudioLLM/CosyVoice2-0.5B:charles",
    "daniel": "FunAudioLLM/CosyVoice2-0.5B:daniel",
    "emily": "FunAudioLLM/CosyVoice2-0.5B:emily",
    "fiona": "FunAudioLLM/CosyVoice2-0.5B:fiona",
    "grace": "FunAudioLLM/CosyVoice2-0.5B:grace",
    "helen": "FunAudioLLM/CosyVoice2-0.5B:helen",
}

# Default voice mapping by persona style
VOICE_STYLE_MAP = {
    "male_professional": "alex",
    "male_broadcast": "benjamin",
    "male_documentary": "charles",
    "female_warm": "emily",
    "female_professional": "fiona",
    "female_ethereal": "grace",
}


class SiliconFlowTTSProvider(BaseTTSProvider):
    """SiliconFlow TTS via OpenAI-compatible /audio/speech endpoint."""

    name = "siliconflow"

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs: Any):
        super().__init__(api_key, base_url or "https://api.siliconflow.cn/v1", **kwargs)
        self.model = kwargs.get("model", "FunAudioLLM/CosyVoice2-0.5B")

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        # Resolve voice ID
        voice_id = request.voice_id
        if voice_id in SILICONFLOW_VOICES:
            voice_id = SILICONFLOW_VOICES[voice_id]
        elif voice_id in VOICE_STYLE_MAP:
            voice_id = SILICONFLOW_VOICES[VOICE_STYLE_MAP[voice_id]]
        elif not voice_id or ":" not in voice_id:
            # Default voice
            voice_id = SILICONFLOW_VOICES["alex"]

        # Use plain text (SSML not supported by this endpoint)
        text = request.text
        if not text and request.ssml:
            # Strip SSML tags, use plain text
            import re
            text = re.sub(r'<[^>]+>', '', request.ssml)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": self.model,
            "input": text,
            "voice": voice_id,
            "response_format": "mp3",
        }

        if request.speed != 1.0:
            payload["speed"] = request.speed

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/audio/speech",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()

            audio_data = resp.content

        # Estimate duration from audio size (rough: mp3 ~16KB/s at 128kbps)
        estimated_duration = len(audio_data) / 16000

        return TTSResponse(
            audio_data=audio_data,
            duration=estimated_duration,
            format="mp3",
            metadata={
                "provider": "siliconflow",
                "model": self.model,
                "voice": voice_id,
            },
        )

    async def list_voices(self) -> list[dict[str, Any]]:
        return [
            {"id": k, "full_id": v, "provider": "siliconflow"}
            for k, v in SILICONFLOW_VOICES.items()
        ]
