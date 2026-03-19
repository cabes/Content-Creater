"""Build pipelines from workflow configuration, registering all available stages."""
from __future__ import annotations

from src.core.pipeline import Pipeline


# Stage registry - lazy imports to avoid circular dependencies
def _get_stage_registry() -> dict:
    from src.stages.topic_engine.stage import TopicEngineStage
    from src.stages.text_creator.stage import TextCreatorStage
    from src.stages.compliance.stage import ComplianceStage
    from src.stages.tts_engine.stage import TTSEngineStage
    from src.stages.video_maker.stage import VideoMakerStage
    from src.stages.article_formatter.stage import ArticleFormatterStage
    from src.stages.publisher.stage import PublisherStage

    return {
        "topic_engine": TopicEngineStage,
        "text_creator": TextCreatorStage,
        "compliance": ComplianceStage,
        "tts_engine": TTSEngineStage,
        "video_maker": VideoMakerStage,
        "article_formatter": ArticleFormatterStage,
        "publisher": PublisherStage,
    }


def build_pipeline(workflow_config: dict) -> Pipeline:
    """Build a Pipeline from workflow config, adding stages that are defined.

    Stages listed in workflow_config["stages"] are instantiated in order.
    Stages not present in the registry are skipped with a warning.
    """
    import structlog
    logger = structlog.get_logger()

    name = workflow_config.get("name", "unnamed")
    pipeline = Pipeline(name=name)
    registry = _get_stage_registry()

    stages_defs = workflow_config.get("stages", [])
    for stage_def in stages_defs:
        if isinstance(stage_def, dict):
            stage_name = next(iter(stage_def))
        elif isinstance(stage_def, str):
            stage_name = stage_def
        else:
            continue

        cls = registry.get(stage_name)
        if cls is None:
            logger.warning("pipeline_builder.unknown_stage", stage=stage_name)
            continue

        pipeline.add_stage(cls())

    return pipeline
