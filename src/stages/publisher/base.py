"""Abstract base class for platform publishers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.core.models import Platform, PublishResult, PipelineStatus


@dataclass
class PlatformContent:
    """Content prepared for a specific platform."""
    platform: Platform
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    video_path: str = ""
    cover_image_path: str = ""
    article_html: str = ""
    audio_path: str = ""
    images: list[str] = field(default_factory=list)
    short_text: str = ""
    comment_pin: str = ""  # Pinned comment (for CTA)
    scheduled_time: str = ""  # ISO format
    extra: dict[str, Any] = field(default_factory=dict)


class BasePublisher(ABC):
    """Abstract base for platform publishers."""

    platform: Platform
    name: str = ""

    def __init__(self, account_config: dict[str, Any] | None = None, **kwargs: Any):
        self.account_config = account_config or {}
        self.extra = kwargs
        self._logged_in = False

    @abstractmethod
    async def login(self) -> bool:
        """Authenticate with the platform. Returns True on success."""
        ...

    @abstractmethod
    async def publish(self, content: PlatformContent) -> PublishResult:
        """Publish content to the platform."""
        ...

    async def check_status(self, post_id: str) -> dict[str, Any]:
        """Check the status of a published post."""
        return {"post_id": post_id, "status": "unknown"}

    async def pin_comment(self, post_id: str, comment: str) -> bool:
        """Pin a comment on a post (for CTA)."""
        return False

    async def get_metrics(self, post_id: str) -> dict[str, Any]:
        """Get engagement metrics for a post."""
        return {}
