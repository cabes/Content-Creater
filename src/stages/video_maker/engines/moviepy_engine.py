"""MoviePy v2 engine: full-screen images with Ken Burns, dark overlay, styled text."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import structlog
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from src.core.models import Scene, Storyboard
from .base import BaseVideoEngine

logger = structlog.get_logger()

FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def _find_cjk_font(bold: bool = False) -> str:
    for f in [FONT_BOLD_PATH if bold else FONT_PATH,
              "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"]:
        if Path(f).exists():
            return f
    return ""


CJK_FONT = _find_cjk_font(False)
CJK_FONT_BOLD = _find_cjk_font(True)

DOMAIN_THEMES = {
    "finance": {
        "gradient": [(8, 18, 48), (15, 35, 75)],
        "accent": (50, 140, 255),
        "highlight": (255, 200, 50),
        "overlay_opacity": 140,  # 0-255, dark overlay on images
    },
    "geopolitics": {
        "gradient": [(18, 12, 12), (40, 20, 20)],
        "accent": (220, 60, 60),
        "highlight": (255, 200, 80),
        "overlay_opacity": 130,
    },
    "mystical": {
        "gradient": [(12, 4, 32), (30, 12, 60)],
        "accent": (160, 80, 220),
        "highlight": (255, 215, 0),
        "overlay_opacity": 120,
    },
    "knowledge": {
        "gradient": [(10, 24, 38), (22, 48, 72)],
        "accent": (40, 180, 220),
        "highlight": (100, 230, 160),
        "overlay_opacity": 135,
    },
}

# Size
W, H = 1920, 1080


class MoviePyEngine(BaseVideoEngine):
    """Full-screen image compositing with Ken Burns, overlays, and styled CJK text."""

    name = "moviepy"

    def __init__(self, output_dir: Path | None = None, **kwargs: Any):
        super().__init__(output_dir, **kwargs)
        self.domain = kwargs.get("domain", "finance")
        self.theme = DOMAIN_THEMES.get(self.domain, DOMAIN_THEMES["finance"])

    def supports_scene_type(self, scene_type: str) -> bool:
        return True

    async def render_scene(self, scene: Scene, assets: dict[str, Path]) -> Path:
        from moviepy import ImageClip, CompositeVideoClip, vfx

        duration = max(2.0, scene.duration)
        size = (W, H)
        clips = []

        # ── 1. Background: full-screen image or gradient ──
        image_path = self._find_image_asset(assets)
        if image_path:
            # Full-screen image with Ken Burns
            base_frame = self._prepare_fullscreen_image(image_path)
            img_clip = ImageClip(base_frame).with_duration(duration)

            # Ken Burns: always apply subtle zoom for motion
            zoom_speed = 0.03 / duration
            if scene.camera_move == "pull_out":
                img_clip = img_clip.resized(lambda t: 1.06 - zoom_speed * t)
            else:  # push_in or default
                img_clip = img_clip.resized(lambda t: 1.0 + zoom_speed * t)

            clips.append(img_clip)

            # Dark gradient overlay for text readability
            overlay = self._make_text_overlay(size)
            clips.append(ImageClip(overlay).with_duration(duration))
        else:
            # Fallback: gradient background
            bg = ImageClip(self._make_gradient_bg(size)).with_duration(duration)
            clips.append(bg)

        # ── 2. Top-left branding / scene indicator ──
        indicator = self._render_scene_indicator(scene.scene_type, size)
        if indicator is not None:
            clips.append(
                ImageClip(indicator).with_duration(duration)
                .with_effects([vfx.CrossFadeIn(0.4)])
            )

        # ── 3. Main text (large, centered or positioned) ──
        if scene.text_overlay:
            text_frame = self._render_main_text(scene.text_overlay, size, has_image=bool(image_path))
            clips.append(
                ImageClip(text_frame).with_duration(duration)
                .with_effects([vfx.CrossFadeIn(0.6)])
            )

        # ── 4. Bottom subtitle bar ──
        if scene.text_overlay:
            sub_frame = self._render_subtitle_bar(scene.text_overlay, size)
            clips.append(
                ImageClip(sub_frame).with_duration(duration)
                .with_position(("center", "bottom"))
                .with_start(0.3)
                .with_effects([vfx.CrossFadeIn(0.4)])
            )

        # ── Compose + crossfade between scenes ──
        clip = CompositeVideoClip(clips, size=size).with_duration(duration)
        clip = clip.with_effects([vfx.CrossFadeIn(0.5), vfx.CrossFadeOut(0.5)])

        output_path = self.output_dir / f"scene_{uuid4().hex[:8]}.mp4"
        clip.write_videofile(
            str(output_path), fps=24, codec="libx264",
            audio=False, logger=None, preset="ultrafast",
        )
        clip.close()
        return output_path

    async def render_storyboard(
        self, storyboard: Storyboard, assets: dict[str, Path],
        audio_path: Path | None = None,
    ) -> Path:
        from moviepy import concatenate_videoclips, VideoFileClip, AudioFileClip, ColorClip

        scene_clips = []
        for i, scene in enumerate(storyboard.scenes):
            scene_assets = {k: v for k, v in assets.items() if f"scene_{i}" in k}
            try:
                clip_path = await self.render_scene(scene, scene_assets)
                scene_clips.append(VideoFileClip(str(clip_path)))
            except Exception as e:
                logger.warning("moviepy.scene_failed", scene=i, error=str(e))
                fb = ColorClip(size=(W, H), color=self.theme["gradient"][0]).with_duration(scene.duration)
                scene_clips.append(fb)

        if not scene_clips:
            raise ValueError("No scenes rendered")

        # Concatenate with crossfade padding
        final = concatenate_videoclips(scene_clips, method="compose", padding=-0.5)

        if audio_path and audio_path.exists():
            audio = AudioFileClip(str(audio_path))
            if audio.duration > final.duration:
                gap = audio.duration - final.duration
                last = scene_clips[-1]
                scene_clips[-1] = last.with_duration(last.duration + gap)
                final = concatenate_videoclips(scene_clips, method="compose", padding=-0.5)
            final = final.with_audio(audio)

        output_path = self.output_dir / f"video_{uuid4().hex[:8]}.mp4"
        final.write_videofile(
            str(output_path), fps=24, codec="libx264",
            audio_codec="aac", logger=None, preset="ultrafast",
        )
        final.close()
        for c in scene_clips:
            c.close()

        logger.info("moviepy.render_complete", path=str(output_path))
        return output_path

    # ── Visual helpers ──

    def _find_image_asset(self, assets: dict[str, Path]) -> Path | None:
        """Find the first valid image in assets."""
        for path in assets.values():
            if path and path.exists() and path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                return path
        return None

    def _prepare_fullscreen_image(self, image_path: Path) -> np.ndarray:
        """Load image, crop/resize to fill 1920x1080 (cover mode)."""
        img = Image.open(image_path).convert("RGB")

        # Cover crop: resize so shortest side fills target, then center crop
        target_ratio = W / H
        img_ratio = img.width / img.height

        if img_ratio > target_ratio:
            # Image is wider — fit height, crop width
            new_h = H
            new_w = int(H * img_ratio)
        else:
            # Image is taller — fit width, crop height
            new_w = W
            new_h = int(W / img_ratio)

        # Slight oversize for Ken Burns (6% margin)
        new_w = int(new_w * 1.06)
        new_h = int(new_h * 1.06)

        img = img.resize((new_w, new_h), Image.LANCZOS)

        # Center crop
        left = (new_w - W) // 2
        top = (new_h - H) // 2
        img = img.crop((left, top, left + W, top + H))

        return np.array(img)

    def _make_text_overlay(self, size: tuple[int, int]) -> np.ndarray:
        """Dark gradient overlay: darker at bottom (for text), lighter at top (show image)."""
        w, h = size
        overlay = np.zeros((h, w, 4), dtype=np.uint8)
        opacity = self.theme["overlay_opacity"]

        for y in range(h):
            # Vignette: darker at top and bottom, lighter in middle
            top_fade = max(0, 1.0 - y / (h * 0.3))  # Top 30%
            bottom_fade = max(0, (y - h * 0.6) / (h * 0.4))  # Bottom 40%
            alpha = int(opacity * max(top_fade * 0.5, bottom_fade))
            overlay[y, :, 3] = min(255, alpha)

        return overlay

    def _make_gradient_bg(self, size: tuple[int, int]) -> np.ndarray:
        w, h = size
        c1 = np.array(self.theme["gradient"][0], dtype=np.float64)
        c2 = np.array(self.theme["gradient"][1], dtype=np.float64)
        bg = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(h):
            bg[y, :] = (c1 + (c2 - c1) * y / h).astype(np.uint8)
        return bg

    def _render_scene_indicator(self, scene_type: str, size: tuple[int, int]) -> np.ndarray | None:
        """Small top-left indicator (accent bar + scene type)."""
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        accent = self.theme["accent"]

        # Top-left accent bar
        draw.rectangle([(40, 30), (46, 80)], fill=(*accent, 220))

        # Small scene type label
        font = self._get_font(18)
        label_map = {
            "text_animation": "FOCUS", "data_reveal": "DATA",
            "chart": "CHART", "image": "INSIGHT",
            "comparison": "VS", "annotation": "NOTE",
        }
        label = label_map.get(scene_type, "")
        if label:
            draw.text((56, 42), label, font=font, fill=(*accent, 200))

        return np.array(img)

    def _render_main_text(self, text: str, size: tuple[int, int], has_image: bool = False) -> np.ndarray:
        """Render main text — positioned lower when image is present."""
        w, h = size
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Font size based on text length
        n = len(text)
        if n <= 8:
            fs = 72
        elif n <= 14:
            fs = 60
        elif n <= 22:
            fs = 50
        else:
            fs = 40

        font = self._get_font(fs, bold=True)

        # Wrap text
        max_w = w - 240
        lines = self._wrap_text(text, font, max_w, draw)

        total_h = len(lines) * (fs + 14)

        # Position: center-lower when image bg, true center when no image
        if has_image:
            start_y = int(h * 0.42) - total_h // 2
        else:
            start_y = (h - total_h) // 2 - 30

        highlight = self.theme["highlight"]

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            x = (w - lw) // 2
            y = start_y + i * (fs + 14)

            # Shadow (offset + blur effect)
            for ox, oy in [(3, 3), (2, 2), (1, 1)]:
                draw.text((x + ox, y + oy), line, font=font, fill=(0, 0, 0, 120))

            # Main text
            draw.text((x, y), line, font=font, fill=(255, 255, 255, 250))

        # Accent underline
        ul_y = start_y + total_h + 16
        ul_w = min(360, max_w // 2)
        ul_x = (w - ul_w) // 2
        draw.rectangle([(ul_x, ul_y), (ul_x + ul_w, ul_y + 4)], fill=(*highlight, 220))

        return np.array(img)

    def _render_subtitle_bar(self, text: str, size: tuple[int, int]) -> np.ndarray:
        """Bottom subtitle bar with frosted-glass look."""
        w, _ = size
        bar_h = 72
        img = Image.new("RGBA", (w, bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark gradient bar
        for y in range(bar_h):
            alpha = int(180 * (y / bar_h))  # Darker towards bottom
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        # Top accent line
        accent = self.theme["accent"]
        draw.rectangle([(0, 0), (w, 2)], fill=(*accent, 160))

        # Text
        font = self._get_font(26)
        display = text[:45] + "..." if len(text) > 45 else text
        bbox = draw.textbbox((0, 0), display, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, (bar_h - 26) // 2), display, font=font, fill=(255, 255, 255, 230))

        return np.array(img)

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        path = CJK_FONT_BOLD if bold else CJK_FONT
        if path:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
        lines, cur = [], ""
        for ch in text:
            test = cur + ch
            if draw.textbbox((0, 0), test, font=font)[2] > max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur = test
        if cur:
            lines.append(cur)
        return lines
