"""LLM provider factory."""
from __future__ import annotations

from typing import Any

from src.core.config import get_settings

from .base import BaseLLM, LLMMessage, LLMResponse
from .claude import ClaudeLLM
from .openai_compat import OpenAICompatLLM

__all__ = ["BaseLLM", "LLMMessage", "LLMResponse", "get_llm"]

_PROVIDERS: dict[str, type[BaseLLM]] = {
    "claude": ClaudeLLM,
    "openai": OpenAICompatLLM,
    "domestic": OpenAICompatLLM,  # Most domestic models are OpenAI-compatible
}


def get_llm(provider: str | None = None, **overrides: Any) -> BaseLLM:
    """Factory: create an LLM instance from config + optional overrides."""
    settings = get_settings()
    provider = provider or settings.llm.provider

    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise ValueError(f"Unknown LLM provider: {provider}. Available: {list(_PROVIDERS)}")

    return cls(
        api_key=overrides.get("api_key", settings.llm.api_key),
        model=overrides.get("model", settings.llm.model),
        base_url=overrides.get("base_url", settings.llm.base_url),
    )
