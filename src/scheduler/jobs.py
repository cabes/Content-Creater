"""Celery task definitions and scheduling."""
from __future__ import annotations

import asyncio
from typing import Any

import structlog

logger = structlog.get_logger()


def run_async(coro: Any) -> Any:
    """Helper to run async code from sync Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _run_pipeline(workflow_name: str, domain: str) -> dict[str, Any]:
    """Run a named pipeline for a domain."""
    from src.core.config import CONFIG_DIR
    from src.core.pipeline import PipelineContext, load_workflow
    from src.core.pipeline_builder import build_pipeline

    workflow_config = load_workflow(CONFIG_DIR / "workflows" / f"{workflow_name}.yaml")

    for stage_def in workflow_config.get("stages", []):
        if isinstance(stage_def, dict) and "topic_engine" in stage_def:
            stage_def["topic_engine"]["domain"] = domain

    context = PipelineContext(workflow_config=workflow_config)
    pipeline = build_pipeline(workflow_config)
    run = await pipeline.run(context)

    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "content_title": run.content.title if run.content else None,
    }


async def _run_hook_pipeline(domain: str = "finance") -> dict[str, Any]:
    return await _run_pipeline("hook_pipeline", domain)


async def _run_value_pipeline(domain: str = "finance") -> dict[str, Any]:
    return await _run_pipeline("value_pipeline", domain)


# ── Celery task wrappers (imported when Celery is available) ──

def register_celery_tasks(celery_app: Any) -> None:
    """Register pipeline tasks with a Celery app."""

    @celery_app.task(name="run_hook_pipeline")
    def run_hook_pipeline(domain: str = "finance") -> dict:
        logger.info("celery.hook_pipeline.start", domain=domain)
        result = run_async(_run_hook_pipeline(domain))
        logger.info("celery.hook_pipeline.done", result=result)
        return result

    @celery_app.task(name="run_value_pipeline")
    def run_value_pipeline(domain: str = "finance") -> dict:
        logger.info("celery.value_pipeline.start", domain=domain)
        result = run_async(_run_value_pipeline(domain))
        logger.info("celery.value_pipeline.done", result=result)
        return result

    return {
        "run_hook_pipeline": run_hook_pipeline,
        "run_value_pipeline": run_value_pipeline,
    }


# ── Celery Beat schedule ──

CELERY_BEAT_SCHEDULE = {
    "hook-finance-every-2h": {
        "task": "run_hook_pipeline",
        "schedule": 7200.0,  # 2 hours
        "args": ("finance",),
    },
    "hook-mystical-every-3h": {
        "task": "run_hook_pipeline",
        "schedule": 10800.0,  # 3 hours
        "args": ("mystical",),
    },
    "hook-geopolitics-every-4h": {
        "task": "run_hook_pipeline",
        "schedule": 14400.0,  # 4 hours
        "args": ("geopolitics",),
    },
    "value-finance-weekly": {
        "task": "run_value_pipeline",
        "schedule": 604800.0,  # weekly
        "args": ("finance",),
    },
    "value-mystical-weekly": {
        "task": "run_value_pipeline",
        "schedule": 604800.0,
        "args": ("mystical",),
    },
}
