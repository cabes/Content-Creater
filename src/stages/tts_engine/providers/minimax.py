"""Minimax T2A Pro TTS provider - best Chinese emotion expressiveness."""
from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from .base import BaseTTSProvider, TTSRequest, TTSResponse

logger = structlog.get_logger()

MINIMAX_TTS_URL = "https://api.minimax.chat/v1/t2a_v2"


class MinimaxTTSProvider(BaseTTSProvider):
    """Minimax T2A Pro API adapter."""

    name = "minimax"

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs: Any):
        super().__init__(api_key, base_url or MINIMAX_TTS_URL, **kwargs)
        self.group_id = kwargs.get("group_id", "")

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Build request payload
        payload: dict[str, Any] = {
            "model": "speech-01-turbo",
            "text": request.ssml or request.text,
            "stream": False,
            "voice_setting": {
                "voice_id": request.voice_id or "male-qn-qingse",
                "speed": request.speed,
                "vol": request.volume,
                "pitch": int(request.pitch),
            },
            "audio_setting": {
                "sample_rate": request.sample_rate,
                "format": request.output_format,
            },
        }

        if request.emotion:
            payload["voice_setting"]["emotion"] = request.emotion

        url = self.base_url
        if self.group_id:
            url = f"{url}?GroupId={self.group_id}"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Extract audio
        audio_data = b""
        if "data" in data and "audio" in data["data"]:
            import base64
            audio_data = base64.b64decode(data["data"]["audio"])

        extra_info = data.get("extra_info", {})
        duration = extra_info.get("audio_length", 0) / 1000.0  # ms to seconds

        return TTSResponse(
            audio_data=audio_data,
            duration=duration,
            sample_rate=request.sample_rate,
            format=request.output_format,
            metadata={
                "provider": "minimax",
                "voice_id": request.voice_id,
                "usage": extra_info.get("usage", {}),
            },
        )

    async def list_voices(self) -> list[dict[str, Any]]:
        return [
            {"id": "male-qn-qingse", "name": "青涩青年", "gender": "male", "style": "young"},
            {"id": "male-qn-jingying", "name": "精英青年", "gender": "male", "style": "professional"},
            {"id": "male-qn-badao", "name": "霸道青年", "gender": "male", "style": "bold"},
            {"id": "male-qn-daxuesheng", "name": "大学生", "gender": "male", "style": "casual"},
            {"id": "female-shaonv", "name": "少女", "gender": "female", "style": "young"},
            {"id": "female-yujie", "name": "御姐", "gender": "female", "style": "mature"},
            {"id": "female-chengshu", "name": "成熟女性", "gender": "female", "style": "professional"},
            {"id": "presenter_male", "name": "男播音", "gender": "male", "style": "broadcast"},
            {"id": "presenter_female", "name": "女播音", "gender": "female", "style": "broadcast"},
            {"id": "audiobook_male_1", "name": "有声书男1", "gender": "male", "style": "narrative"},
            {"id": "audiobook_female_1", "name": "有声书女1", "gender": "female", "style": "narrative"},
        ]

    async def clone_voice(self, name: str, audio_data: bytes) -> str:
        logger.info("minimax.clone_voice", name=name, audio_size=len(audio_data))
        # Minimax voice cloning requires separate API endpoint
        # Placeholder for actual implementation
        raise NotImplementedError("Minimax voice cloning requires manual setup via their console")
