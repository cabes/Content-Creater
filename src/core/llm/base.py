"""Abstract base class for LLM providers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str


class LLMResponse(BaseModel):
    content: str
    model: str = ""
    usage: dict[str, int] = {}
    raw: dict[str, Any] = {}


class BaseLLM(ABC):
    """Abstract base for LLM providers."""

    def __init__(self, api_key: str, model: str = "", base_url: str = "", **kwargs: Any):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.extra = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion from the LLM."""
        ...

    async def generate_text(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Convenience method: generate text from a simple prompt string."""
        messages: list[LLMMessage] = []
        if system:
            messages.append(LLMMessage(role="system", content=system))
        messages.append(LLMMessage(role="user", content=prompt))
        response = await self.generate(
            messages, max_tokens=max_tokens, temperature=temperature, **kwargs
        )
        return response.content
