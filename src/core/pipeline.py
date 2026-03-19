"""Pipeline orchestration engine for content creation workflows."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
import yaml

from src.core.models import PipelineRun, PipelineStatus, StageResult

logger = structlog.get_logger()


class Stage(ABC):
    """Abstract base class for pipeline stages."""

    name: str = ""

    @abstractmethod
    async def execute(self, context: PipelineContext) -> StageResult:
        """Execute this stage with the given pipeline context."""
        ...

    async def should_skip(self, context: PipelineContext) -> bool:
        """Check if this stage should be skipped."""
        return False


class PipelineContext:
    """Shared context passed between pipeline stages."""

    def __init__(self, workflow_config: dict[str, Any] | None = None):
        self.workflow_config = workflow_config or {}
        self.data: dict[str, Any] = {}
        self.run = PipelineRun(
            workflow_name=self.workflow_config.get("name", "unnamed"),
        )

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get_stage_config(self, stage_name: str) -> dict[str, Any]:
        """Get configuration for a specific stage from workflow config."""
        stages = self.workflow_config.get("stages", [])
        for stage_def in stages:
            if isinstance(stage_def, dict) and stage_name in stage_def:
                return stage_def[stage_name]
        return {}


class Pipeline:
    """Orchestrates execution of a sequence of stages."""

    def __init__(self, name: str = "default"):
        self.name = name
        self.stages: list[Stage] = []
        self._log = logger.bind(pipeline=name)

    def add_stage(self, stage: Stage) -> "Pipeline":
        self.stages.append(stage)
        return self

    async def run(self, context: PipelineContext | None = None) -> PipelineRun:
        """Execute all stages in sequence."""
        if context is None:
            context = PipelineContext()

        context.run.status = PipelineStatus.RUNNING
        context.run.workflow_name = self.name
        self._log.info("pipeline.started", stages=[s.name for s in self.stages])

        for stage in self.stages:
            if await stage.should_skip(context):
                result = StageResult(
                    stage_name=stage.name,
                    status=PipelineStatus.SKIPPED,
                )
                context.run.stage_results.append(result)
                self._log.info("stage.skipped", stage=stage.name)
                continue

            self._log.info("stage.started", stage=stage.name)
            start = time.monotonic()

            try:
                result = await stage.execute(context)
                result.duration_seconds = time.monotonic() - start
                result.completed_at = datetime.utcnow()
                context.run.stage_results.append(result)

                if result.status == PipelineStatus.FAILED:
                    self._log.error(
                        "stage.failed",
                        stage=stage.name,
                        error=result.error,
                    )
                    context.run.status = PipelineStatus.FAILED
                    break

                self._log.info(
                    "stage.completed",
                    stage=stage.name,
                    duration=f"{result.duration_seconds:.1f}s",
                )

            except Exception as exc:
                result = StageResult(
                    stage_name=stage.name,
                    status=PipelineStatus.FAILED,
                    error=str(exc),
                    duration_seconds=time.monotonic() - start,
                    completed_at=datetime.utcnow(),
                )
                context.run.stage_results.append(result)
                context.run.status = PipelineStatus.FAILED
                self._log.exception("stage.exception", stage=stage.name)
                break
        else:
            context.run.status = PipelineStatus.COMPLETED

        context.run.completed_at = datetime.utcnow()
        self._log.info(
            "pipeline.finished",
            status=context.run.status.value,
            stages_run=len(context.run.stage_results),
        )
        return context.run


def load_workflow(path: str | Path) -> dict[str, Any]:
    """Load a workflow definition from YAML."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("workflow", data)
