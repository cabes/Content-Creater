"""Volcengine (火山引擎) TTS provider - ByteDance, good Chinese naturalness."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from .base import BaseTTSProvider, TTSRequest, TTSResponse

logger = structlog.get_logger()


class VolcengineTTSProvider(BaseTTSProvider):
    """Volcengine TTS API adapter."""

    name = "volcengine"

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs: Any):
        super().__init__(api_key, base_url or "https://openspeech.bytedance.com/api/v1/tts", **kwargs)
        self.app_id = kwargs.get("app_id", "")

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        headers = {
            "Authorization": f"Bearer;{self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "app": {"appid": self.app_id, "cluster": "volcano_tts"},
            "user": {"uid": "content_creater"},
            "audio": {
                "voice_type": request.voice_id or "zh_female_cancan",
                "encoding": request.output_format.upper(),
                "speed_ratio": request.speed,
                "volume_ratio": request.volume,
                "pitch_ratio": request.pitch,
            },
            "request": {
                "text": request.text,
                "operation": "query",
            },
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self.base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        audio_data = b""
        if "data" in data:
            import base64
            audio_data = base64.b64decode(data["data"])

        return TTSResponse(
            audio_data=audio_data,
            format=request.output_format,
            metadata={"provider": "volcengine", "voice_id": request.voice_id},
        )

    async def list_voices(self) -> list[dict[str, Any]]:
        return [
            {"id": "zh_female_cancan", "name": "灿灿", "gender": "female"},
            {"id": "zh_male_chunhou", "name": "醇厚", "gender": "male"},
            {"id": "zh_female_shuangkuai", "name": "爽快", "gender": "female"},
            {"id": "zh_male_yangguang", "name": "阳光", "gender": "male"},
        ]
