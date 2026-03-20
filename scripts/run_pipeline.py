#!/usr/bin/env python3
"""CLI script to manually run a pipeline. Useful for testing."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run content creation pipeline")
    parser.add_argument(
        "--workflow",
        choices=["hook", "value"],
        default="hook",
        help="Pipeline type (default: hook)",
    )
    parser.add_argument(
        "--domain",
        choices=["finance", "geopolitics", "mystical", "knowledge"],
        default="finance",
        help="Content domain (default: finance)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    from src.core.config import CONFIG_DIR
    from src.core.pipeline import PipelineContext, load_workflow
    from src.core.pipeline_builder import build_pipeline

    workflow_file = f"{args.workflow}_pipeline.yaml"
    workflow_config = load_workflow(CONFIG_DIR / "workflows" / workflow_file)

    # Inject domain
    for stage_def in workflow_config.get("stages", []):
        if isinstance(stage_def, dict) and "topic_engine" in stage_def:
            stage_def["topic_engine"]["domain"] = args.domain

    context = PipelineContext(workflow_config=workflow_config)
    pipeline = build_pipeline(workflow_config)

    print(f"Running {args.workflow} pipeline for domain: {args.domain}")
    print("=" * 60)

    run = await pipeline.run(context)

    print(f"\nPipeline status: {run.status.value}")
    for sr in run.stage_results:
        status_icon = "✓" if sr.status.value == "completed" else "✗"
        print(f"  {status_icon} {sr.stage_name}: {sr.status.value} ({sr.duration_seconds:.1f}s)")
        if sr.error:
            print(f"    Error: {sr.error}")

    if run.content:
        print(f"\n{'=' * 60}")
        print(f"Title: {run.content.title}")
        print(f"Summary: {run.content.summary}")
        print(f"Quality: {run.content.quality_score}")
        print(f"Sections: {len(run.content.sections)}")
        print(f"\nTTS Script:\n{run.content.tts_script[:500]}...")
        if run.content.short_copy:
            print(f"\nShort Copy:\n{run.content.short_copy}")
        if run.content.cta_hooks:
            print(f"\nCTA Hooks:")
            for cta in run.content.cta_hooks:
                print(f"  - {cta}")
        if run.content.compliance_notes:
            print(f"\nCompliance: {run.content.compliance_notes}")
        if run.content.disclaimers:
            print(f"Disclaimers: {len(run.content.disclaimers)} added")

        if args.output:
            output_data = run.content.model_dump(mode="json")
            with open(args.output, "w") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"\nFull output written to: {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
