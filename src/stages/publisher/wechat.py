"""WeChat Official Account publisher."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from src.core.models import Platform, PublishResult, PipelineStatus
from .base import BasePublisher, PlatformContent

logger = structlog.get_logger()


class WechatPublisher(BasePublisher):
    """Publish articles to WeChat Official Account via API."""

    platform = Platform.WECHAT
    name = "wechat"

    def __init__(self, account_config: dict[str, Any] | None = None, **kwargs: Any):
        super().__init__(account_config, **kwargs)
        self.app_id = self.account_config.get("app_id", "")
        self.app_secret = self.account_config.get("app_secret", "")
        self.access_token = ""

    async def login(self) -> bool:
        """Get access token from WeChat API."""
        if not self.app_id or not self.app_secret:
            logger.warning("wechat.no_credentials")
            return False

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://api.weixin.qq.com/cgi-bin/token",
                    params={
                        "grant_type": "client_credential",
                        "appid": self.app_id,
                        "secret": self.app_secret,
                    },
                )
                data = resp.json()
                self.access_token = data.get("access_token", "")
                self._logged_in = bool(self.access_token)
                return self._logged_in
        except Exception as e:
            logger.error("wechat.login_failed", error=str(e))
            return False

    async def publish(self, content: PlatformContent) -> PublishResult:
        if not self._logged_in:
            await self.login()
        if not self._logged_in:
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.FAILED,
                error="Not logged in to WeChat",
            )

        try:
            # Step 1: Upload cover image (if exists)
            thumb_media_id = ""
            if content.cover_image_path:
                thumb_media_id = await self._upload_image(content.cover_image_path)

            # Step 2: Create draft article
            article = {
                "title": content.title[:64],
                "content": content.article_html,
                "digest": content.description[:120],
                "content_source_url": "",
                "need_open_comment": 1,
            }
            if thumb_media_id:
                article["thumb_media_id"] = thumb_media_id

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={self.access_token}",
                    json={"articles": [article]},
                )
                data = resp.json()

            if "media_id" in data:
                media_id = data["media_id"]
                logger.info("wechat.draft_created", media_id=media_id)
                return PublishResult(
                    platform=self.platform,
                    status=PipelineStatus.COMPLETED,
                    post_id=media_id,
                )
            else:
                return PublishResult(
                    platform=self.platform,
                    status=PipelineStatus.FAILED,
                    error=f"WeChat API error: {data}",
                )

        except Exception as e:
            logger.exception("wechat.publish_failed")
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.FAILED,
                error=str(e),
            )

    async def _upload_image(self, image_path: str) -> str:
        """Upload image to WeChat and return media_id."""
        from pathlib import Path
        path = Path(image_path)
        if not path.exists():
            return ""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                files = {"media": (path.name, path.read_bytes(), "image/jpeg")}
                resp = await client.post(
                    f"https://api.weixin.qq.com/cgi-bin/material/add_material",
                    params={"access_token": self.access_token, "type": "image"},
                    files=files,
                )
                data = resp.json()
                return data.get("media_id", "")
        except Exception:
            return ""
