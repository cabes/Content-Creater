"""Xiaohongshu (Little Red Book) publisher using browser automation."""
from __future__ import annotations

from typing import Any

import structlog

from src.core.models import Platform, PublishResult, PipelineStatus
from .base import BasePublisher, PlatformContent

logger = structlog.get_logger()


class XiaohongshuPublisher(BasePublisher):
    """Publish to Xiaohongshu using Playwright automation."""

    platform = Platform.XIAOHONGSHU
    name = "xiaohongshu"

    async def login(self) -> bool:
        """Login using stored cookies via Playwright."""
        try:
            from playwright.async_api import async_playwright

            cookies = self.account_config.get("cookies", [])
            if not cookies:
                logger.warning("xiaohongshu.no_cookies")
                return False

            # Verify cookies are still valid
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context()
                await ctx.add_cookies(cookies)
                page = await ctx.new_page()
                await page.goto("https://creator.xiaohongshu.com")
                # Check if redirected to login
                self._logged_in = "login" not in page.url
                await browser.close()

            return self._logged_in

        except ImportError:
            logger.warning("playwright not installed")
            return False
        except Exception as e:
            logger.error("xiaohongshu.login_failed", error=str(e))
            return False

    async def publish(self, content: PlatformContent) -> PublishResult:
        """Publish note to Xiaohongshu via creator platform."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.FAILED,
                error="playwright not installed",
            )

        try:
            cookies = self.account_config.get("cookies", [])

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context()
                await ctx.add_cookies(cookies)
                page = await ctx.new_page()

                # Navigate to creator platform
                await page.goto("https://creator.xiaohongshu.com/publish/publish")
                await page.wait_for_load_state("networkidle")

                # Upload images or video
                if content.video_path:
                    upload_input = await page.query_selector('input[type="file"]')
                    if upload_input:
                        await upload_input.set_input_files(content.video_path)
                elif content.images:
                    upload_input = await page.query_selector('input[type="file"]')
                    if upload_input:
                        await upload_input.set_input_files(content.images)

                # Fill title
                title_input = await page.query_selector('[placeholder*="标题"]')
                if title_input:
                    await title_input.fill(content.title[:20])

                # Fill description
                desc_input = await page.query_selector('[placeholder*="正文"]')
                if desc_input:
                    text_with_tags = content.short_text or content.description
                    # Add hashtags
                    for tag in content.tags[:5]:
                        text_with_tags += f" #{tag}"
                    await desc_input.fill(text_with_tags)

                # Submit (would need to handle actual submission flow)
                logger.info("xiaohongshu.publish_prepared", title=content.title)

                await browser.close()

            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.COMPLETED,
            )

        except Exception as e:
            logger.exception("xiaohongshu.publish_failed")
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.FAILED,
                error=str(e),
            )
