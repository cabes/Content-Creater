"""Topic Engine stage: orchestrates topic discovery and selection."""
from __future__ import annotations

from datetime import date

import structlog

from src.core.models import ContentDomain, ContentLayer, PipelineStatus, StageResult
from src.core.pipeline import PipelineContext, Stage
from src.stages.topic_engine.analyzer import analyze_and_select_topics
from src.stages.topic_engine.sentiment.analyzer import deep_sentiment_analysis
from src.stages.topic_engine.sentiment.collector import collect_comments_from_trending
from src.stages.topic_engine.sources.calendar import get_upcoming_events
from src.stages.topic_engine.sources.dailyhot import fetch_domain_trending

logger = structlog.get_logger()


class TopicEngineStage(Stage):
    """Discover and select content topics based on trends and sentiment."""

    name = "topic_engine"

    async def execute(self, context: PipelineContext) -> StageResult:
        config = context.get_stage_config(self.name)
        mode = config.get("mode", "emotion_hunter")
        domain_str = config.get("domain", context.get("domain", "finance"))
        domain = ContentDomain(domain_str)
        layer = ContentLayer.HOOK if mode == "emotion_hunter" else ContentLayer.VALUE
        max_topics = config.get("max_topics", 5)
        do_sentiment = config.get("sentiment_scan", True)

        try:
            # 1. Fetch trending topics
            logger.info("topic_engine.fetching_trends", domain=domain.value)
            trending = await fetch_domain_trending(domain.value)
            logger.info("topic_engine.trends_fetched", count=len(trending))

            # 2. Sentiment analysis (if enabled)
            sentiment_signals = []
            if do_sentiment and trending:
                collected = await collect_comments_from_trending(trending)
                sentiment_signals = await deep_sentiment_analysis(collected, domain.value)
                logger.info("topic_engine.sentiment_done", signals=len(sentiment_signals))

            # 3. Calendar events
            calendar_events = get_upcoming_events(domain.value, days_ahead=3)

            # 4. LLM analysis and selection
            topics = await analyze_and_select_topics(
                trending=trending,
                sentiment_signals=sentiment_signals,
                domain=domain,
                layer=layer,
                max_topics=max_topics,
                calendar_events=calendar_events,
            )
            logger.info("topic_engine.topics_selected", count=len(topics))

            if not topics:
                return StageResult(
                    stage_name=self.name,
                    status=PipelineStatus.FAILED,
                    error="No suitable topics found",
                )

            # Store in context
            context.set("topics", topics)
            context.set("selected_topic", topics[0])  # Best topic
            context.set("domain", domain)
            context.set("content_layer", layer)

            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.COMPLETED,
                output={
                    "topics_count": len(topics),
                    "selected_title": topics[0].title,
                    "domain": domain.value,
                    "layer": layer.value,
                },
            )

        except Exception as e:
            logger.exception("topic_engine.failed")
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error=str(e),
            )
