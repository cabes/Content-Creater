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

            # 2. Generate assets
            assets: dict[str, Path] = {}
            for i, scene in enumerate(storyboard.scenes):
                for j, asset_desc in enumerate(scene.assets_needed):
                    asset_key = f"scene_{i}_asset_{j}"
                    asset_path = await self._generate_asset(
                        asset_desc, scene, content.domain.value, assets_dir
                    )
                    if asset_path:
                        assets[asset_key] = asset_path

                # Generate charts from scene data
                if scene.data.get("chart_type"):
                    chart_path = await generate_chart(
                        chart_type=scene.data["chart_type"],
                        data=scene.data,
                        output_dir=assets_dir,
                    )
                    if chart_path:
                        assets[f"scene_{i}_chart"] = chart_path

            logger.info("video_maker.assets_generated", count=len(assets))

            # 3. Select engine
            engine_names = config.get("engines", [storyboard.engine_hint or "moviepy"])
            if isinstance(engine_names, str):
                engine_names = [engine_names]
            engine_name = engine_names[0]  # Use first available
            engine = get_video_engine(engine_name, output_dir=video_dir)

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

    async def _generate_asset(
        self,
        description: str,
        scene: Any,
        domain: str,
        output_dir: Path,
    ) -> Path | None:
        """Generate or fetch an asset for a scene."""
        desc_lower = description.lower()

        # Try AI image generation first
        if any(kw in desc_lower for kw in ["图", "illustration", "背景", "场景"]):
            path = await generate_ai_image(description, domain=domain, output_dir=output_dir)
            if path:
                return path

        # Try stock media
        results = await search_pexels(description, per_page=1)
        if results:
            path = await download_media(results[0]["url"], output_dir)
            if path:
                return path

        return None
