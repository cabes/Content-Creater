"""Publisher stage: distribute content to multiple platforms."""
from __future__ import annotations

from typing import Any

import structlog

from src.core.config import get_account_config
from src.core.models import (
    Platform,
    PipelineStatus,
    PublishResult,
    StageResult,
    StructuredContent,
    AudioAsset,
)
from src.core.pipeline import PipelineContext, Stage
from src.stages.publisher import PlatformContent, get_publisher

logger = structlog.get_logger()


class PublisherStage(Stage):
    """Publish content to configured platforms."""

    name = "publisher"

    async def execute(self, context: PipelineContext) -> StageResult:
        config = context.get_stage_config(self.name)
        content: StructuredContent | None = context.get("content")
        if content is None:
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error="No content in context",
            )

        audio: AudioAsset | None = context.get("audio")
        video_path: str = context.get("video_path", "")
        article_html: str = context.get("article_html", "")

        # Determine target platforms
        platforms_config = config.get("platforms", [])
        if platforms_config:
            platforms = [Platform(p) for p in platforms_config]
        else:
            # Get from topic's target platforms
            topic = context.get("selected_topic")
            platforms = topic.target_platforms if topic else [Platform.BILIBILI]

        # Load account config
        account_config = get_account_config(content.account_id)

        results: list[PublishResult] = []
        cta_inject = config.get("cta_inject", True)

        for platform in platforms:
            try:
                # Prepare platform-specific content
                platform_content = _prepare_content(
                    content=content,
                    platform=platform,
                    audio=audio,
                    video_path=video_path,
                    article_html=article_html,
                    cta_inject=cta_inject,
                )

                # Get platform-specific config from account
                platform_config = account_config.get("platforms", {}).get(platform.value, {})
                publisher = get_publisher(platform, account_config={**account_config, **platform_config})

                # Publish
                result = await publisher.publish(platform_content)
                results.append(result)

                # Pin CTA comment if supported
                if cta_inject and result.post_id and platform_content.comment_pin:
                    await publisher.pin_comment(result.post_id, platform_content.comment_pin)

                logger.info(
                    "publisher.published",
                    platform=platform.value,
                    status=result.status.value,
                    url=result.url or "(pending)",
                )

            except Exception as e:
                logger.exception("publisher.platform_failed", platform=platform.value)
                results.append(PublishResult(
                    platform=platform,
                    status=PipelineStatus.FAILED,
                    error=str(e),
                ))

        # Store results
        context.run.publish_results = results

        # Determine overall status
        successes = sum(1 for r in results if r.status == PipelineStatus.COMPLETED)
        total = len(results)

        if successes == 0 and total > 0:
            status = PipelineStatus.FAILED
        elif successes < total:
            status = PipelineStatus.COMPLETED  # Partial success is still completed
        else:
            status = PipelineStatus.COMPLETED

        return StageResult(
            stage_name=self.name,
            status=status,
            output={
                "platforms_attempted": total,
                "platforms_succeeded": successes,
                "results": [
                    {"platform": r.platform.value, "status": r.status.value, "url": r.url}
                    for r in results
                ],
            },
        )


def _prepare_content(
    content: StructuredContent,
    platform: Platform,
    audio: AudioAsset | None = None,
    video_path: str = "",
    article_html: str = "",
    cta_inject: bool = True,
) -> PlatformContent:
    """Prepare content for a specific platform."""
    # Base content
    pc = PlatformContent(
        platform=platform,
        title=content.title,
        description=content.summary,
        tags=content.tags,
        video_path=video_path,
        audio_path=audio.file_path if audio else "",
    )

    # Platform-specific adaptations
    if platform == Platform.WECHAT:
        pc.article_html = article_html or content.article_text
        pc.title = content.title[:64]

    elif platform == Platform.XIAOHONGSHU:
        pc.short_text = content.short_copy or content.summary
        pc.title = content.title[:20]
        # XHS prefers emoji-rich content
        pc.tags = [f"#{t}" for t in content.tags[:5]]

    elif platform == Platform.DOUYIN:
        pc.title = content.title[:30]
        pc.description = content.short_copy or content.summary

    elif platform == Platform.BILIBILI:
        pc.title = content.title[:80]

    elif platform == Platform.PODCAST:
        pc.title = content.title
        pc.description = content.summary

    # CTA injection
    if cta_inject and content.cta_hooks:
        from src.stages.compliance.disclaimer import get_disclaimer
        disclaimer = get_disclaimer(content.domain.value, "comment_pin")
        cta = content.cta_hooks[0]
        pc.comment_pin = f"{cta}\n{disclaimer}" if disclaimer else cta

    return pc
