"""Bilibili video publisher."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import structlog

from src.core.models import Platform, PublishResult, PipelineStatus
from .base import BasePublisher, PlatformContent

logger = structlog.get_logger()


class BilibiliPublisher(BasePublisher):
    """Publish videos to Bilibili using their API."""

    platform = Platform.BILIBILI
    name = "bilibili"

    def __init__(self, account_config: dict[str, Any] | None = None, **kwargs: Any):
        super().__init__(account_config, **kwargs)
        self.cookies: dict[str, str] = {}
        self.csrf = ""

    async def login(self) -> bool:
        """Login using stored cookies/tokens."""
        cookies = self.account_config.get("cookies", {})
        if not cookies:
            logger.warning("bilibili.no_cookies", hint="Set cookies in account config")
            return False
        self.cookies = cookies
        self.csrf = cookies.get("bili_jct", "")
        self._logged_in = bool(self.csrf)
        return self._logged_in

    async def publish(self, content: PlatformContent) -> PublishResult:
        if not self._logged_in:
            await self.login()
        if not self._logged_in:
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.FAILED,
                error="Not logged in to Bilibili",
            )

        try:
            # Step 1: Upload video (simplified - actual implementation needs chunked upload)
            video_path = Path(content.video_path)
            if not video_path.exists():
                return PublishResult(
                    platform=self.platform,
                    status=PipelineStatus.FAILED,
                    error=f"Video file not found: {content.video_path}",
                )

            # Step 2: Submit video info
            # This is a simplified version. Real implementation needs:
            # 1. Pre-upload to get upload URL
            # 2. Chunked upload of video file
            # 3. Submit with video metadata
            submit_data = {
                "title": content.title[:80],  # Bilibili max 80 chars
                "desc": content.description[:2000],
                "tag": ",".join(content.tags[:12]),  # Max 12 tags
                "tid": 21,  # Default: 日常 category
                "copyright": 1,  # Original content
                "csrf": self.csrf,
            }

            logger.info("bilibili.publish", title=content.title, tags=content.tags)

            # Placeholder for actual API call
            # In production, implement the full Bilibili upload flow
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.COMPLETED,
                url="",  # Would be set after actual upload
                post_id="",
            )

        except Exception as e:
            logger.exception("bilibili.publish_failed")
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.FAILED,
                error=str(e),
            )

    async def get_metrics(self, post_id: str) -> dict[str, Any]:
        """Get video metrics from Bilibili API."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://api.bilibili.com/x/web-interface/view?bvid={post_id}"
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    stat = data.get("stat", {})
                    return {
                        "views": stat.get("view", 0),
                        "likes": stat.get("like", 0),
                        "coins": stat.get("coin", 0),
                        "favorites": stat.get("favorite", 0),
                        "shares": stat.get("share", 0),
                        "comments": stat.get("reply", 0),
                        "danmaku": stat.get("danmaku", 0),
                    }
        except Exception as e:
            logger.warning("bilibili.metrics_failed", error=str(e))
        return {}
