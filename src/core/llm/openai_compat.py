"""OpenAI-compatible LLM adapter (works with OpenAI, domestic models, etc.)."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from .base import BaseLLM, LLMMessage, LLMResponse

logger = structlog.get_logger()


class OpenAICompatLLM(BaseLLM):
    """OpenAI-compatible API adapter."""

    def __init__(self, api_key: str, model: str = "", base_url: str = "", **kwargs: Any):
        super().__init__(api_key, model or "gpt-4o", base_url, **kwargs)
        self._base_url = (base_url or "https://api.openai.com/v1") + "/chat/completions"

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(self._base_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=data.get("model", self.model),
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
            raw=data,
        )
