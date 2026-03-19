"""Video compositor: final assembly of scenes + audio + subtitles."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from src.core.models import AudioAsset, AudioTimestamp

logger = structlog.get_logger()


async def composite_final_video(
    video_path: Path,
    audio_path: Path | None = None,
    subtitle_path: Path | None = None,
    output_path: Path | None = None,
    aspect_ratio: str = "16:9",
) -> Path:
    """Compose final video with audio and subtitles."""
    if output_path is None:
        output_path = video_path.parent / f"final_{uuid4().hex[:8]}.mp4"

    try:
        from moviepy import VideoFileClip, AudioFileClip

        video = VideoFileClip(str(video_path))

        # Add audio if provided
        if audio_path and audio_path.exists():
            audio = AudioFileClip(str(audio_path))
            video = video.with_audio(audio)

        # Handle aspect ratio conversion
        if aspect_ratio == "9:16":  # Vertical (Douyin/XHS)
            video = _convert_to_vertical(video)
        elif aspect_ratio == "1:1":  # Square
            video = _convert_to_square(video)

        video.write_videofile(
            str(output_path),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        video.close()

        logger.info("compositor.done", output=str(output_path), aspect=aspect_ratio)
        return output_path

    except ImportError:
        logger.warning("moviepy not installed, returning raw video")
        if output_path != video_path:
            import shutil
            shutil.copy2(video_path, output_path)
        return output_path


def _convert_to_vertical(video: Any) -> Any:
    """Convert 16:9 video to 9:16 (vertical) with letterboxing."""
    from moviepy import CompositeVideoClip, ColorClip

    target_w, target_h = 1080, 1920
    # Scale video to fit width
    scaled = video.resized(width=target_w)
    bg = ColorClip(size=(target_w, target_h), color=(0, 0, 0)).with_duration(video.duration)
    result = CompositeVideoClip([bg, scaled.with_position("center")])
    if video.audio:
        result = result.with_audio(video.audio)
    return result


def _convert_to_square(video: Any) -> Any:
    """Convert 16:9 video to 1:1 (square) with letterboxing."""
    from moviepy import CompositeVideoClip, ColorClip

    target = 1080
    scaled = video.resized(width=target)
    bg = ColorClip(size=(target, target), color=(0, 0, 0)).with_duration(video.duration)
    result = CompositeVideoClip([bg, scaled.with_position("center")])
    if video.audio:
        result = result.with_audio(video.audio)
    return result


async def generate_subtitle_file(
    timestamps: list[AudioTimestamp],
    output_path: Path,
    format: str = "ass",
) -> Path:
    """Generate subtitle file from audio timestamps."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "srt":
        lines = []
        for i, ts in enumerate(timestamps):
            start = _format_srt_time(ts.start_time)
            end = _format_srt_time(ts.end_time)
            lines.append(f"{i+1}")
            lines.append(f"{start} --> {end}")
            lines.append(ts.text)
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")

    elif format == "ass":
        # ASS format with styling
        header = """[Script Info]
Title: Generated Subtitles
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,PingFang SC,48,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,60,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        events = []
        for ts in timestamps:
            start = _format_ass_time(ts.start_time)
            end = _format_ass_time(ts.end_time)
            events.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{ts.text}")

        output_path.write_text(header + "\n".join(events), encoding="utf-8")

    return output_path


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_ass_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
