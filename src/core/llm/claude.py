"""Claude (Anthropic) LLM adapter."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from .base import BaseLLM, LLMMessage, LLMResponse

logger = structlog.get_logger()

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class ClaudeLLM(BaseLLM):
    """Anthropic Claude API adapter."""

    def __init__(self, api_key: str, model: str = "", base_url: str = "", **kwargs: Any):
        super().__init__(api_key, model or "claude-sonnet-4-20250514", base_url, **kwargs)
        self._base_url = base_url or ANTHROPIC_API_URL

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        # Separate system message from conversation messages
        system_text = ""
        conv_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg.role == "system":
                system_text = msg.content
            else:
                conv_messages.append({"role": msg.role, "content": msg.content})

        if not conv_messages:
            conv_messages = [{"role": "user", "content": ""}]

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": conv_messages,
        }
        if system_text:
            payload["system"] = system_text

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self._base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block["text"]

        usage = data.get("usage", {})
        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            usage={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            raw=data,
        )
