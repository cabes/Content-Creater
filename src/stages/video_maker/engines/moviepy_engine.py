"""MoviePy v2 engine: image+text compositing with gradient backgrounds and text animations."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import structlog
from PIL import Image, ImageDraw, ImageFont

from src.core.models import Scene, Storyboard
from .base import BaseVideoEngine

logger = structlog.get_logger()

# Chinese font path (install fonts-noto-cjk)
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

# Fallback font search
def _find_cjk_font(bold: bool = False) -> str:
    candidates = [
        FONT_BOLD_PATH if bold else FONT_PATH,
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for f in candidates:
        if Path(f).exists():
            return f
    return ""

CJK_FONT = _find_cjk_font(False)
CJK_FONT_BOLD = _find_cjk_font(True)

# Color themes per domain
DOMAIN_THEMES = {
    "finance": {
        "gradient": [(10, 25, 60), (20, 50, 100)],
        "accent": (50, 130, 240),
        "highlight": (255, 200, 50),
        "text": (255, 255, 255),
        "subtitle_bg": (10, 25, 60, 200),
    },
    "geopolitics": {
        "gradient": [(20, 20, 30), (50, 25, 25)],
        "accent": (200, 50, 50),
        "highlight": (255, 200, 80),
        "text": (255, 255, 255),
        "subtitle_bg": (20, 20, 30, 200),
    },
    "mystical": {
        "gradient": [(15, 5, 40), (40, 15, 80)],
        "accent": (160, 80, 220),
        "highlight": (255, 215, 0),
        "text": (255, 255, 255),
        "subtitle_bg": (15, 5, 40, 200),
    },
    "knowledge": {
        "gradient": [(15, 30, 45), (30, 60, 90)],
        "accent": (40, 160, 220),
        "highlight": (100, 220, 160),
        "text": (255, 255, 255),
        "subtitle_bg": (15, 30, 45, 200),
    },
}


class MoviePyEngine(BaseVideoEngine):
    """Image+text compositing engine using MoviePy v2 with proper CJK support."""

    name = "moviepy"

    def __init__(self, output_dir: Path | None = None, **kwargs: Any):
        super().__init__(output_dir, **kwargs)
        self.domain = kwargs.get("domain", "finance")
        self.theme = DOMAIN_THEMES.get(self.domain, DOMAIN_THEMES["finance"])

    def supports_scene_type(self, scene_type: str) -> bool:
        return True  # Fallback engine handles everything

    async def render_scene(self, scene: Scene, assets: dict[str, Path]) -> Path:
        from moviepy import ImageClip, CompositeVideoClip, vfx

        duration = max(1.0, scene.duration)
        size = (1920, 1080)
        clips = []

        # 1. Gradient background (always)
        bg_frame = self._make_gradient_bg(size)
        bg = ImageClip(bg_frame).with_duration(duration)
        clips.append(bg)

        # 2. Decorative elements (accent lines, subtle patterns)
        deco = self._make_decorations(size, scene.scene_type)
        if deco is not None:
            deco_clip = ImageClip(deco).with_duration(duration).with_position("center")
            clips.append(deco_clip)

        # 3. Image asset (if available)
        has_image = False
        for asset_key, asset_path in assets.items():
            if asset_path and asset_path.exists() and asset_path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                try:
                    img = (
                        ImageClip(str(asset_path))
                        .with_duration(duration)
                        .resized(height=int(size[1] * 0.7))
                        .with_position("center")
                    )
                    if scene.camera_move == "push_in":
                        img = img.resized(lambda t: 1 + 0.04 * t / duration)
                    elif scene.camera_move == "pull_out":
                        img = img.resized(lambda t: 1.08 - 0.04 * t / duration)
                    clips.append(img)
                    has_image = True
                    break
                except Exception as e:
                    logger.warning("moviepy.image_load_failed", error=str(e))

        # 4. If no image — render large stylized text as the main visual
        if not has_image and scene.text_overlay:
            main_text_frame = self._render_main_text(
                scene.text_overlay, size, scene.scene_type
            )
            main_clip = (
                ImageClip(main_text_frame)
                .with_duration(duration)
                .with_position("center")
                .with_effects([vfx.CrossFadeIn(0.8)])
            )
            clips.append(main_clip)

        # 5. Bottom subtitle bar (always, if there's text)
        if scene.text_overlay:
            subtitle_frame = self._render_subtitle_bar(scene.text_overlay, size)
            sub_clip = (
                ImageClip(subtitle_frame)
                .with_duration(duration)
                .with_position(("center", "bottom"))
                .with_start(0.3)
                .with_effects([vfx.CrossFadeIn(0.5)])
            )
            clips.append(sub_clip)

        # Compose
        clip = CompositeVideoClip(clips, size=size).with_duration(duration)
        output_path = self.output_dir / f"scene_{uuid4().hex[:8]}.mp4"
        clip.write_videofile(
            str(output_path), fps=24, codec="libx264",
            audio=False, logger=None,
            preset="ultrafast",
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
            concatenate_videoclips, VideoFileClip, AudioFileClip, ColorClip,
        )

        scene_clips = []
        for i, scene in enumerate(storyboard.scenes):
            scene_assets = {k: v for k, v in assets.items() if f"scene_{i}" in k}
            try:
                clip_path = await self.render_scene(scene, scene_assets)
                clip = VideoFileClip(str(clip_path))
                scene_clips.append(clip)
            except Exception as e:
                logger.warning("moviepy.scene_render_failed", scene=i, error=str(e))
                fallback = ColorClip(
                    size=(1920, 1080), color=self.theme["gradient"][0],
                ).with_duration(scene.duration)
                scene_clips.append(fallback)

        if not scene_clips:
            raise ValueError("No scenes rendered")

        final = concatenate_videoclips(scene_clips, method="compose")

        if audio_path and audio_path.exists():
            audio = AudioFileClip(str(audio_path))
            if audio.duration > final.duration:
                # Extend last scene to fill gap instead of black frames
                gap = audio.duration - final.duration
                last_clip = scene_clips[-1]
                extended_last = last_clip.with_duration(last_clip.duration + gap)
                scene_clips[-1] = extended_last
                final = concatenate_videoclips(scene_clips, method="compose")
            final = final.with_audio(audio)

        output_path = self.output_dir / f"video_{uuid4().hex[:8]}.mp4"
        final.write_videofile(
            str(output_path), fps=24, codec="libx264",
            audio_codec="aac", logger=None,
            preset="ultrafast",
        )
        final.close()
        for clip in scene_clips:
            clip.close()

        logger.info("moviepy.render_complete", path=str(output_path))
        return output_path

    # ── Visual generation helpers ──

    def _make_gradient_bg(self, size: tuple[int, int]) -> np.ndarray:
        """Create a vertical gradient background."""
        w, h = size
        c1 = np.array(self.theme["gradient"][0], dtype=np.float64)
        c2 = np.array(self.theme["gradient"][1], dtype=np.float64)
        gradient = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            ratio = y / h
            color = c1 * (1 - ratio) + c2 * ratio
            gradient[y, :] = color.astype(np.uint8)
        return gradient

    def _make_decorations(self, size: tuple[int, int], scene_type: str) -> np.ndarray | None:
        """Create subtle decorative elements (accent lines, dots)."""
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        accent = self.theme["accent"]

        # Top accent line
        draw.rectangle([(0, 0), (w, 4)], fill=(*accent, 180))

        # Bottom accent line
        draw.rectangle([(0, h - 4), (w, h)], fill=(*accent, 120))

        # Side accent bars
        draw.rectangle([(0, 0), (6, h)], fill=(*accent, 60))
        draw.rectangle([(w - 6, 0), (w, h)], fill=(*accent, 60))

        # Subtle grid dots
        for x in range(100, w, 200):
            for y in range(100, h, 200):
                draw.ellipse([(x-1, y-1), (x+1, y+1)], fill=(*accent, 30))

        return np.array(img)

    def _render_main_text(
        self, text: str, size: tuple[int, int], scene_type: str,
    ) -> np.ndarray:
        """Render large centered text as main visual (when no image available)."""
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Choose font size based on text length
        if len(text) <= 8:
            font_size = 80
        elif len(text) <= 15:
            font_size = 64
        elif len(text) <= 25:
            font_size = 52
        else:
            font_size = 42

        font = self._get_font(font_size, bold=True)

        # Calculate text bbox for centering
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        # If text is too wide, wrap it
        if tw > w - 200:
            lines = self._wrap_text(text, font, w - 200, draw)
        else:
            lines = [text]

        # Draw each line centered
        total_height = len(lines) * (font_size + 16)
        start_y = (h - total_height) // 2 - 40  # Slightly above center

        accent = self.theme["accent"]
        highlight = self.theme["highlight"]

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            x = (w - lw) // 2
            y = start_y + i * (font_size + 16)

            # Text shadow
            draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 150))
            # Main text
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

        # Accent underline below text block
        line_y = start_y + total_height + 20
        line_w = min(400, tw)
        line_x = (w - line_w) // 2
        draw.rectangle(
            [(line_x, line_y), (line_x + line_w, line_y + 4)],
            fill=(*highlight, 200),
        )

        return np.array(img)

    def _render_subtitle_bar(self, text: str, size: tuple[int, int]) -> np.ndarray:
        """Render a semi-transparent subtitle bar at the bottom."""
        w, h = size
        bar_h = 80
        img = Image.new("RGBA", (w, bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Semi-transparent background bar
        bg_color = self.theme["subtitle_bg"]
        draw.rectangle([(0, 0), (w, bar_h)], fill=bg_color)

        # Accent line at top of bar
        accent = self.theme["accent"]
        draw.rectangle([(0, 0), (w, 3)], fill=(*accent, 200))

        # Subtitle text
        font_size = 28
        font = self._get_font(font_size)

        # Truncate if too long
        display_text = text
        if len(display_text) > 40:
            display_text = display_text[:38] + "..."

        bbox = draw.textbbox((0, 0), display_text, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        y = (bar_h - font_size) // 2

        draw.text((x, y), display_text, font=font, fill=(255, 255, 255, 240))

        return np.array(img)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """Get a CJK-compatible font."""
        font_path = CJK_FONT_BOLD if bold else CJK_FONT
        if font_path:
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _wrap_text(
        self, text: str, font: ImageFont.FreeTypeFont, max_width: int,
        draw: ImageDraw.ImageDraw,
    ) -> list[str]:
        """Wrap text to fit within max_width."""
        lines = []
        current = ""
        for char in text:
            test = current + char
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
        return lines
