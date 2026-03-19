"""Remotion engine: Node.js-based programmatic video (knowledge animations, data-driven)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from src.core.models import Scene, Storyboard
from .base import BaseVideoEngine

logger = structlog.get_logger()

SUPPORTED_TYPES = {
    "chart", "flowchart", "data_reveal", "text_animation",
    "comparison", "knowledge_animation",
}


class RemotionEngine(BaseVideoEngine):
    """Remotion (Node.js) video rendering engine for knowledge animations."""

    name = "remotion"

    def __init__(self, output_dir: Path | None = None, **kwargs: Any):
        super().__init__(output_dir, **kwargs)
        self.remotion_dir = kwargs.get("remotion_dir", Path("remotion"))
        self.remotion_url = kwargs.get("remotion_url", "http://localhost:3000")

    def supports_scene_type(self, scene_type: str) -> bool:
        return scene_type in SUPPORTED_TYPES

    async def render_scene(self, scene: Scene, assets: dict[str, Path]) -> Path:
        # Remotion renders full compositions, not individual scenes
        raise NotImplementedError("Use render_storyboard for Remotion")

    async def render_storyboard(
        self,
        storyboard: Storyboard,
        assets: dict[str, Path],
        audio_path: Path | None = None,
    ) -> Path:
        """Render video using Remotion CLI or API."""
        # Generate props JSON for Remotion
        props = {
            "scenes": [
                {
                    "type": s.scene_type,
                    "description": s.description,
                    "duration": s.duration,
                    "textOverlay": s.text_overlay,
                    "cameraMove": s.camera_move,
                    "transition": s.transition,
                    "data": s.data,
                    "assets": {k: str(v) for k, v in assets.items() if f"scene_{i}" in k}
                }
                for i, s in enumerate(storyboard.scenes)
            ],
            "totalDuration": storyboard.total_duration,
            "audioPath": str(audio_path) if audio_path else None,
            "fps": 30,
        }

        props_path = self.output_dir / f"props_{uuid4().hex[:8]}.json"
        props_path.write_text(json.dumps(props, ensure_ascii=False))

        output_path = self.output_dir / f"remotion_{uuid4().hex[:8]}.mp4"

        try:
            # Try Remotion CLI render
            result = subprocess.run(
                [
                    "npx", "remotion", "render",
                    "--props", str(props_path),
                    "--output", str(output_path),
                    "--codec", "h264",
                    "KnowledgeAnimation",
                ],
                cwd=str(self.remotion_dir),
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode == 0:
                logger.info("remotion.render_complete", path=str(output_path))
                return output_path
            else:
                logger.error("remotion.render_failed", stderr=result.stderr[:500])
                raise RuntimeError(f"Remotion render failed: {result.stderr[:200]}")

        except FileNotFoundError:
            logger.warning("remotion.npx_not_found, falling back to API")
            # Fallback: try HTTP API to Remotion service
            return await self._render_via_api(props, output_path)

    async def _render_via_api(self, props: dict, output_path: Path) -> Path:
        """Render via Remotion HTTP service (Docker container)."""
        import httpx

        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(
                f"{self.remotion_url}/api/render",
                json=props,
            )
            resp.raise_for_status()

            if resp.headers.get("content-type", "").startswith("video/"):
                output_path.write_bytes(resp.content)
                return output_path

            data = resp.json()
            video_url = data.get("output_url", "")
            if video_url:
                video_resp = await client.get(video_url)
                output_path.write_bytes(video_resp.content)
                return output_path

        raise RuntimeError("Remotion API did not return video")
