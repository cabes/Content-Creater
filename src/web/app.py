"""FastAPI web application for monitoring and manual control."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.models import ContentDomain, ContentLayer

app = FastAPI(
    title="Content Creater",
    description="AI Content Creation Pipeline - Control Panel",
    version="0.1.0",
)


class PipelineRunRequest(BaseModel):
    """Request to trigger a pipeline run."""
    workflow: str = "hook_pipeline"
    domain: str = "finance"
    topic_override: str | None = None


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str = "0.1.0"


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
    )


@app.get("/api/config")
async def get_config() -> dict[str, Any]:
    """Get current configuration (redacted)."""
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "llm_provider": settings.llm.provider,
        "llm_model": settings.llm.model,
        "tts_provider": settings.tts.provider,
        "topic_scan_interval": settings.topic_engine.scan_interval_hours,
        "compliance_enabled": settings.compliance.enabled,
    }


@app.post("/api/pipeline/run")
async def trigger_pipeline(request: PipelineRunRequest) -> dict[str, Any]:
    """Manually trigger a pipeline run."""
    from src.core.pipeline import PipelineContext, load_workflow
    from src.core.pipeline_builder import build_pipeline
    from src.core.config import CONFIG_DIR

    workflow_path = CONFIG_DIR / "workflows" / f"{request.workflow}.yaml"
    if not workflow_path.exists():
        raise HTTPException(status_code=404, detail=f"Workflow not found: {request.workflow}")

    workflow_config = load_workflow(workflow_path)

    # Inject domain into config
    for stage_def in workflow_config.get("stages", []):
        if isinstance(stage_def, dict) and "topic_engine" in stage_def:
            stage_def["topic_engine"]["domain"] = request.domain

    context = PipelineContext(workflow_config=workflow_config)
    if request.topic_override:
        context.set("topic_override", request.topic_override)

    pipeline = build_pipeline(workflow_config)

    # Run pipeline
    run = await pipeline.run(context)

    return {
        "run_id": str(run.id),
        "status": run.status.value,
        "workflow": request.workflow,
        "domain": request.domain,
        "stages": [
            {
                "name": sr.stage_name,
                "status": sr.status.value,
                "duration": sr.duration_seconds,
                "output": sr.output,
                "error": sr.error or None,
            }
            for sr in run.stage_results
        ],
        "content_title": run.content.title if run.content else None,
        "content_summary": run.content.summary if run.content else None,
    }


@app.get("/api/domains")
async def list_domains() -> list[dict[str, str]]:
    """List available content domains."""
    return [
        {"id": d.value, "name": d.value.title()}
        for d in ContentDomain
    ]


@app.get("/api/workflows")
async def list_workflows() -> list[dict[str, str]]:
    """List available workflows."""
    from src.core.config import CONFIG_DIR
    workflow_dir = CONFIG_DIR / "workflows"
    if not workflow_dir.exists():
        return []
    return [
        {"name": f.stem, "path": str(f)}
        for f in workflow_dir.glob("*.yaml")
    ]
