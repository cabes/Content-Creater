"""Manim engine: mathematical/tutorial animations (3Blue1Brown style)."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from src.core.models import Scene, Storyboard
from .base import BaseVideoEngine

logger = structlog.get_logger()

SUPPORTED_TYPES = {
    "formula", "code_demo", "step_by_step", "geometric",
    "framework", "timeline", "process",
}


class ManimEngine(BaseVideoEngine):
    """Manim animation engine for tutorial/educational content."""

    name = "manim"

    def supports_scene_type(self, scene_type: str) -> bool:
        return scene_type in SUPPORTED_TYPES

    async def render_scene(self, scene: Scene, assets: dict[str, Path]) -> Path:
        raise NotImplementedError("Use render_storyboard for Manim")

    async def render_storyboard(
        self,
        storyboard: Storyboard,
        assets: dict[str, Path],
        audio_path: Path | None = None,
    ) -> Path:
        """Generate and render a Manim scene script."""
        # Generate Manim Python script from storyboard
        script = self._generate_manim_script(storyboard)

        # Write script to temp file
        script_path = self.output_dir / f"manim_scene_{uuid4().hex[:8]}.py"
        script_path.write_text(script)

        output_path = self.output_dir / f"manim_{uuid4().hex[:8]}.mp4"

        try:
            result = subprocess.run(
                [
                    "manim", "render",
                    "-qm",  # Medium quality
                    "--format", "mp4",
                    str(script_path),
                    "GeneratedScene",
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                # Find the output file (manim puts it in media/)
                media_dir = Path("media/videos")
                rendered = list(media_dir.rglob("GeneratedScene.mp4"))
                if rendered:
                    import shutil
                    shutil.move(str(rendered[0]), str(output_path))
                    logger.info("manim.render_complete", path=str(output_path))
                    return output_path

            logger.error("manim.render_failed", stderr=result.stderr[:500])
            raise RuntimeError(f"Manim render failed: {result.stderr[:200]}")

        except FileNotFoundError:
            logger.warning("manim not installed")
            raise

    def _generate_manim_script(self, storyboard: Storyboard) -> str:
        """Generate a Manim Python script from storyboard scenes."""
        lines = [
            "from manim import *",
            "",
            "class GeneratedScene(Scene):",
            "    def construct(self):",
        ]

        for i, scene in enumerate(storyboard.scenes):
            lines.append(f"        # Scene {i+1}: {scene.description[:60]}")

            if scene.scene_type in ("formula", "step_by_step"):
                text = scene.text_overlay or scene.description
                lines.append(f'        text_{i} = Text("{text[:80]}", font_size=36)')
                lines.append(f"        self.play(Write(text_{i}))")
                lines.append(f"        self.wait({scene.duration / 2})")
                lines.append(f"        self.play(FadeOut(text_{i}))")

            elif scene.scene_type == "code_demo":
                code = scene.data.get("code", "# code here")
                lines.append(f'        code_{i} = Code(code="""{code}""", language="python", font_size=24)')
                lines.append(f"        self.play(Create(code_{i}))")
                lines.append(f"        self.wait({scene.duration})")
                lines.append(f"        self.play(FadeOut(code_{i}))")

            elif scene.scene_type == "timeline":
                text = scene.text_overlay or scene.description
                lines.append(f'        title_{i} = Text("{text[:60]}", font_size=42)')
                lines.append(f"        self.play(FadeIn(title_{i}))")
                lines.append(f"        self.wait({scene.duration})")
                lines.append(f"        self.play(FadeOut(title_{i}))")

            else:
                # Default: text reveal
                text = scene.text_overlay or scene.description[:80]
                lines.append(f'        t_{i} = Text("{text}", font_size=36)')
                lines.append(f"        self.play(Write(t_{i}), run_time={min(2, scene.duration/2)})")
                lines.append(f"        self.wait({max(0.5, scene.duration - 2)})")
                lines.append(f"        self.play(FadeOut(t_{i}))")

            lines.append("")

        return "\n".join(lines)
