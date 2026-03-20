"""Publisher factory and registry."""
from __future__ import annotations

from typing import Any

from src.core.models import Platform

from .base import BasePublisher, PlatformContent
from .bilibili import BilibiliPublisher
from .wechat import WechatPublisher
from .xiaohongshu import XiaohongshuPublisher
from .douyin import DouyinPublisher
from .podcast import PodcastPublisher
from .youtube import YouTubePublisher

__all__ = ["BasePublisher", "PlatformContent", "get_publisher"]

_PUBLISHERS: dict[Platform, type[BasePublisher]] = {
    Platform.BILIBILI: BilibiliPublisher,
    Platform.WECHAT: WechatPublisher,
    Platform.XIAOHONGSHU: XiaohongshuPublisher,
    Platform.DOUYIN: DouyinPublisher,
    Platform.PODCAST: PodcastPublisher,
    Platform.YOUTUBE: YouTubePublisher,
}


def get_publisher(platform: Platform, account_config: dict[str, Any] | None = None) -> BasePublisher:
    """Factory: create a publisher for a platform."""
    cls = _PUBLISHERS.get(platform)
    if cls is None:
        raise ValueError(f"No publisher for platform: {platform}. Available: {list(_PUBLISHERS)}")
    return cls(account_config=account_config)
