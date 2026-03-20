"""Video Maker stage: orchestrates storyboard → assets → rendering → compositing."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import structlog

from src.core.config import get_settings
from src.core.models import AudioAsset, PipelineStatus, StageResult, Storyboard, StructuredContent
from src.core.pipeline import PipelineContext, Stage
from src.stages.video_maker.storyboard import generate_storyboard
from src.stages.video_maker.asset_gen import generate_ai_image, generate_chart, search_pexels, download_media
from src.stages.video_maker.asset_gen.ai_image import generate_scene_image
from src.stages.video_maker.engines import get_video_engine
from src.stages.video_maker.compositor import composite_final_video, generate_subtitle_file

logger = structlog.get_logger()


class VideoMakerStage(Stage):
    """Generate video from content + audio."""

    name = "video_maker"

    async def execute(self, context: PipelineContext) -> StageResult:
        config = context.get_stage_config(self.name)
        content: StructuredContent | None = context.get("content")
        audio: AudioAsset | None = context.get("audio")

        if content is None:
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error="No content in context",
            )

        settings = get_settings()
        video_dir = settings.media_dir / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = settings.media_dir / "images"

        try:
            # 1. Generate storyboard
            max_duration = config.get("max_duration", 180)
            storyboard = await generate_storyboard(
                content=content,
                max_scenes=config.get("max_scenes", 15),
                target_duration=float(max_duration),
            )
            context.run.storyboard = storyboard

            # 2. Generate assets for each scene
            assets: dict[str, Path] = {}
            for i, scene in enumerate(storyboard.scenes):
                # Try chart first if scene has chart data
                if scene.data.get("chart_type"):
                    chart_path = await generate_chart(
                        chart_type=scene.data["chart_type"],
                        data=scene.data,
                        output_dir=assets_dir,
                    )
                    if chart_path:
                        assets[f"scene_{i}_chart"] = chart_path
                        continue  # Chart is the visual for this scene

                # Generate AI scene image based on description
                scene_desc = scene.description or scene.text_overlay or ""
                if scene_desc:
                    img_path = await generate_scene_image(
                        scene_type=scene.scene_type,
                        description=scene_desc,
                        domain=content.domain.value,
                        output_dir=assets_dir,
                    )
                    if img_path:
                        assets[f"scene_{i}_img"] = img_path

            logger.info("video_maker.assets_generated", count=len(assets))

            # 3. Select engine
            engine_names = config.get("engines", [storyboard.engine_hint or "moviepy"])
            if isinstance(engine_names, str):
                engine_names = [engine_names]
            engine_name = engine_names[0]  # Use first available
            engine = get_video_engine(engine_name, output_dir=video_dir, domain=content.domain.value)

            # 4. Render
            audio_path = Path(audio.file_path) if audio else None
            video_path = await engine.render_storyboard(
                storyboard=storyboard,
                assets=assets,
                audio_path=audio_path,
            )

            # 5. Generate subtitles
            if audio and audio.timestamps:
                subtitle_path = video_dir / f"subs_{uuid4().hex[:8]}.ass"
                await generate_subtitle_file(audio.timestamps, subtitle_path)

            # 6. Multi-resolution export if needed
            aspect_ratio = config.get("aspect_ratio", storyboard.aspect_ratio)
            if aspect_ratio != "16:9":
                final_path = await composite_final_video(
                    video_path=video_path,
                    audio_path=audio_path,
                    aspect_ratio=aspect_ratio,
                )
            else:
                final_path = video_path

            context.set("video_path", str(final_path))

            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.COMPLETED,
                output={
                    "video_path": str(final_path),
                    "engine": engine_name,
                    "scenes_count": len(storyboard.scenes),
                    "assets_count": len(assets),
                    "duration": storyboard.total_duration,
                    "aspect_ratio": aspect_ratio,
                },
            )

        except Exception as e:
            logger.exception("video_maker.failed")
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error=str(e),
            )

