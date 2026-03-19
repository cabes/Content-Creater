"""Text Creator stage: orchestrates content generation with quality control."""
from __future__ import annotations

import structlog

from src.core.models import ContentLayer, PipelineStatus, StageResult, Topic
from src.core.pipeline import PipelineContext, Stage
from src.stages.text_creator.cta_generator import get_cta_for_content
from src.stages.text_creator.hook_writer import generate_hook_content
from src.stages.text_creator.quality_judge import judge_content_quality
from src.stages.text_creator.value_writer import generate_value_content

logger = structlog.get_logger()

MAX_QUALITY_ITERATIONS = 3


class TextCreatorStage(Stage):
    """Generate structured text content from a topic."""

    name = "text_creator"

    async def execute(self, context: PipelineContext) -> StageResult:
        config = context.get_stage_config(self.name)
        topic: Topic | None = context.get("selected_topic")
        if topic is None:
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error="No topic in context",
            )

        layer = config.get("layer", topic.content_layer.value)
        layer = ContentLayer(layer)
        max_length = config.get("max_length", 800 if layer == ContentLayer.HOOK else 5000)
        auto_link = config.get("auto_link_value_topic", True)

        try:
            # Generate content based on layer
            if layer == ContentLayer.HOOK:
                content = await generate_hook_content(
                    topic=topic,
                    max_length=max_length,
                    auto_link_value=auto_link,
                )
            else:
                content = await generate_value_content(
                    topic=topic,
                    min_length=config.get("min_length", 3000),
                    enable_framework=config.get("framework", True),
                    monetization_anchor=config.get("monetization_anchor", True),
                )

            # Add CTA hooks if not already present
            if not content.cta_hooks:
                content.cta_hooks = get_cta_for_content(topic.domain, layer)

            # Quality check with iteration
            quality_check = config.get("quality_check", True)
            if quality_check:
                min_score = config.get("min_quality_score", 6.0 if layer == ContentLayer.HOOK else 7.0)
                for iteration in range(MAX_QUALITY_ITERATIONS):
                    result = await judge_content_quality(content, min_score=min_score)
                    content.quality_score = result.get("overall_score", 0)
                    content.quality_details = result.get("scores", {})
                    content.iteration_count = iteration + 1

                    if result.get("passed", False):
                        logger.info(
                            "text_creator.quality_passed",
                            score=content.quality_score,
                            iteration=iteration + 1,
                        )
                        break

                    logger.info(
                        "text_creator.quality_below_threshold",
                        score=content.quality_score,
                        min_score=min_score,
                        iteration=iteration + 1,
                    )
                    # In future: re-generate with improvement suggestions
                    # For now, accept after max iterations
                else:
                    logger.warning(
                        "text_creator.quality_max_iterations",
                        final_score=content.quality_score,
                    )

            # Store in context
            context.set("content", content)
            context.run.content = content

            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.COMPLETED,
                output={
                    "title": content.title,
                    "sections_count": len(content.sections),
                    "quality_score": content.quality_score,
                    "layer": layer.value,
                },
            )

        except Exception as e:
            logger.exception("text_creator.failed")
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error=str(e),
            )
