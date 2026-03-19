"""MoviePy v2 engine: image+text compositing, Ken Burns, annotations."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from src.core.models import Scene, Storyboard
from .base import BaseVideoEngine

logger = structlog.get_logger()

# Scene types this engine handles well
SUPPORTED_TYPES = {
    "image", "text_animation", "annotation", "comparison",
    "data_reveal", "chart", "text_overlay",
}


class MoviePyEngine(BaseVideoEngine):
    """Image+text compositing engine using MoviePy v2."""

    name = "moviepy"

    def supports_scene_type(self, scene_type: str) -> bool:
        return scene_type in SUPPORTED_TYPES or True  # Fallback engine handles everything

    async def render_scene(self, scene: Scene, assets: dict[str, Path]) -> Path:
        from moviepy import (
            ImageClip, TextClip, CompositeVideoClip, ColorClip,
            concatenate_videoclips, vfx,
        )

        duration = max(1.0, scene.duration)
        size = (1920, 1080)

        clips = []

        # Background
        bg = ColorClip(size=size, color=(20, 20, 40)).with_duration(duration)
        clips.append(bg)

        # Image asset if available
        for asset_key, asset_path in assets.items():
            if asset_path and asset_path.exists() and asset_path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                try:
                    img = ImageClip(str(asset_path)).with_duration(duration)
                    img = img.resized(height=size[1])
                    if img.w > size[0]:
                        img = img.resized(width=size[0])
                    img = img.with_position("center")

                    # Ken Burns effect (slow zoom)
                    if scene.camera_move == "push_in":
                        img = img.resized(lambda t: 1 + 0.05 * t / duration)
                    elif scene.camera_move == "pull_out":
                        img = img.resized(lambda t: 1.1 - 0.05 * t / duration)

                    clips.append(img)
                    break  # Use first valid image
                except Exception as e:
                    logger.warning("moviepy.image_load_failed", error=str(e))

        # Text overlay
        if scene.text_overlay:
            try:
                txt = (
                    TextClip(
                        text=scene.text_overlay,
                        font_size=48,
                        color="white",
                        size=(size[0] - 200, None),
                    )
                    .with_duration(duration)
                    .with_position(("center", "bottom"))
                    .with_start(0.5)
                    .with_effects([vfx.CrossFadeIn(0.5)])
                )
                clips.append(txt)
            except Exception as e:
                logger.warning("moviepy.text_failed", error=str(e))

        # Compose
        clip = CompositeVideoClip(clips, size=size).with_duration(duration)

        output_path = self.output_dir / f"scene_{uuid4().hex[:8]}.mp4"
        clip.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio=False,
            logger=None,
        )
        clip.close()

        return output_path

    async def render_storyboard(
        self,
        storyboard: Storyboard,
        assets: dict[str, Path],
        audio_path: Path | None = None,
    ) -> Path:
        from moviepy import (
            concatenate_videoclips, VideoFileClip, AudioFileClip,
            CompositeVideoClip, ColorClip,
        )

        scene_clips = []
        for i, scene in enumerate(storyboard.scenes):
            scene_assets = {}
            for key, path in assets.items():
                if f"scene_{i}" in key or key == f"asset_{i}":
                    scene_assets[key] = path

            try:
                clip_path = await self.render_scene(scene, scene_assets)
                clip = VideoFileClip(str(clip_path))
                scene_clips.append(clip)
            except Exception as e:
                logger.warning("moviepy.scene_render_failed", scene=i, error=str(e))
                fallback = ColorClip(size=(1920, 1080), color=(20, 20, 40))
                fallback = fallback.with_duration(scene.duration)
                scene_clips.append(fallback)

        if not scene_clips:
            raise ValueError("No scenes rendered")

        final = concatenate_videoclips(scene_clips, method="compose")

        if audio_path and audio_path.exists():
            audio = AudioFileClip(str(audio_path))
            if audio.duration > final.duration:
                final = final.with_duration(audio.duration)
            final = final.with_audio(audio)

        output_path = self.output_dir / f"video_{uuid4().hex[:8]}.mp4"
        final.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )

        final.close()
        for clip in scene_clips:
            clip.close()

        logger.info("moviepy.render_complete", path=str(output_path))
        return output_path
