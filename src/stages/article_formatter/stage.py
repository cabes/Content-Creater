"""Article formatter stage: Markdown → WeChat HTML."""
from __future__ import annotations

import structlog

from src.core.models import PipelineStatus, StageResult, StructuredContent
from src.core.pipeline import PipelineContext, Stage
from src.stages.article_formatter.wechat import format_wechat_article

logger = structlog.get_logger()


class ArticleFormatterStage(Stage):
    """Format content into platform-specific article formats."""

    name = "article_formatter"

    async def execute(self, context: PipelineContext) -> StageResult:
        content: StructuredContent | None = context.get("content")
        if content is None:
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error="No content in context",
            )

        try:
            # Generate WeChat article HTML
            article_text = content.article_text
            if not article_text:
                # Build from sections
                parts = []
                for sec in content.sections:
                    if sec.heading:
                        parts.append(f"## {sec.heading}")
                    parts.append(sec.body)
                article_text = "\n\n".join(parts)

            html = format_wechat_article(
                title=content.title,
                markdown_text=article_text,
                domain=content.domain.value,
                disclaimers=content.disclaimers,
            )

            context.set("article_html", html)

            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.COMPLETED,
                output={
                    "html_length": len(html),
                    "format": "wechat_html",
                },
            )

        except Exception as e:
            logger.exception("article_formatter.failed")
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error=str(e),
            )
