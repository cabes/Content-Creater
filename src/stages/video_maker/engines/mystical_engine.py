"""Mystical/spiritual atmosphere engine: particles, symbols, dark themes (MoviePy v2)."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from src.core.models import Scene, Storyboard
from .base import BaseVideoEngine

logger = structlog.get_logger()

SUPPORTED_TYPES = {
    "symbol_reveal", "particle_effect", "mandala", "astro_chart",
    "mystical_text", "energy_flow", "cosmic_background",
}

MYSTICAL_PALETTE = {
    "primary": (45, 27, 105),
    "accent": (255, 215, 0),
    "secondary": (155, 89, 182),
    "background": (10, 10, 26),
    "text": (255, 255, 255),
    "glow": (138, 43, 226),
}


class MysticalEngine(BaseVideoEngine):
    """Atmosphere engine for mystical/spiritual content with particle effects."""

    name = "mystical"

    def supports_scene_type(self, scene_type: str) -> bool:
        return scene_type in SUPPORTED_TYPES

    async def render_scene(self, scene: Scene, assets: dict[str, Path]) -> Path:
        from moviepy import ImageClip, TextClip, CompositeVideoClip, ColorClip, vfx

        duration = max(1.0, scene.duration)
        size = (1920, 1080)
        clips = []

        # Dark cosmic background
        bg = ColorClip(size=size, color=MYSTICAL_PALETTE["background"]).with_duration(duration)
        clips.append(bg)

        # Starfield
        starfield = await self._create_starfield(size, duration)
        if starfield:
            clips.append(starfield)

        # Scene-type specific
        if scene.scene_type == "symbol_reveal":
            clip = await self._symbol_reveal(scene, assets, size, duration)
            if clip:
                clips.append(clip)

        elif scene.scene_type == "astro_chart":
            for key, path in assets.items():
                if path and path.exists():
                    img = (
                        ImageClip(str(path))
                        .with_duration(duration)
                        .resized(height=int(size[1] * 0.8))
                        .with_position("center")
                    )
                    clips.append(img)
                    break

        # Text overlay
        if scene.text_overlay:
            try:
                txt = (
                    TextClip(
                        text=scene.text_overlay,
                        font_size=42,
                        color="white",
                        size=(size[0] - 300, None),
                    )
                    .with_duration(duration)
                    .with_position(("center", "bottom"))
                    .with_effects([vfx.CrossFadeIn(1.0), vfx.CrossFadeOut(0.5)])
                )
                clips.append(txt)
            except Exception as e:
                logger.warning("mystical.text_failed", error=str(e))

        clip = CompositeVideoClip(clips, size=size).with_duration(duration)
        output_path = self.output_dir / f"mystical_{uuid4().hex[:8]}.mp4"
        clip.write_videofile(str(output_path), fps=30, codec="libx264", audio=False, logger=None)
        clip.close()
        return output_path

    async def render_storyboard(
        self,
        storyboard: Storyboard,
        assets: dict[str, Path],
        audio_path: Path | None = None,
    ) -> Path:
        from moviepy import concatenate_videoclips, VideoFileClip, AudioFileClip, ColorClip

        scene_clips = []
        for i, scene in enumerate(storyboard.scenes):
            scene_assets = {k: v for k, v in assets.items() if f"scene_{i}" in k}
            try:
                clip_path = await self.render_scene(scene, scene_assets)
                clip = VideoFileClip(str(clip_path))
                scene_clips.append(clip)
            except Exception as e:
                logger.warning("mystical.scene_failed", scene=i, error=str(e))
                fallback = ColorClip(
                    size=(1920, 1080), color=MYSTICAL_PALETTE["background"],
                ).with_duration(scene.duration)
                scene_clips.append(fallback)

        if not scene_clips:
            raise ValueError("No scenes rendered")

        final = concatenate_videoclips(scene_clips, method="compose")

        if audio_path and audio_path.exists():
            audio = AudioFileClip(str(audio_path))
            if audio.duration > final.duration:
                final = final.with_duration(audio.duration)
            final = final.with_audio(audio)

        output_path = self.output_dir / f"mystical_final_{uuid4().hex[:8]}.mp4"
        final.write_videofile(str(output_path), fps=30, codec="libx264", audio_codec="aac", logger=None)
        final.close()
        for clip in scene_clips:
            clip.close()

        logger.info("mystical.render_complete", path=str(output_path))
        return output_path

    async def _create_starfield(self, size: tuple, duration: float) -> Any:
        try:
            import numpy as np
            from moviepy import ImageClip

            frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
            frame[:] = MYSTICAL_PALETTE["background"]

            n_stars = 200
            rng = np.random.default_rng(42)
            ys = rng.integers(0, size[1], n_stars)
            xs = rng.integers(0, size[0], n_stars)
            brightness = rng.integers(100, 255, n_stars)
            for y, x, b in zip(ys, xs, brightness):
                frame[y, x] = (b, b, int(b * 0.9))

            return ImageClip(frame).with_duration(duration)
        except Exception:
            return None

    async def _symbol_reveal(self, scene: Scene, assets: dict[str, Path], size: tuple, duration: float) -> Any:
        try:
            from moviepy import ImageClip, vfx

            for key, path in assets.items():
                if path and path.exists():
                    return (
                        ImageClip(str(path))
                        .with_duration(duration)
                        .resized(height=int(size[1] * 0.5))
                        .with_position("center")
                        .with_effects([vfx.CrossFadeIn(2.0)])
                    )
        except Exception:
            pass
        return None
