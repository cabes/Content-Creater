"""TTS Engine stage: text → broadcast-quality speech audio."""
from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

import structlog

from src.core.config import get_settings
from src.core.models import AudioAsset, PipelineStatus, StageResult, StructuredContent
from src.core.pipeline import PipelineContext, Stage
from src.stages.tts_engine.providers import TTSRequest, get_tts_provider
from src.stages.tts_engine.pronunciation import apply_pronunciation, format_numbers_for_speech
from src.stages.tts_engine.ssml_generator import determine_scene, text_to_ssml
from src.stages.tts_engine.postprocess import AudioPostProcessor
from src.stages.tts_engine.bgm_mixer import mix_bgm, select_bgm
from src.stages.tts_engine.quality_check import check_audio_quality

logger = structlog.get_logger()


class TTSEngineStage(Stage):
    """Convert text content to broadcast-quality speech audio."""

    name = "tts_engine"

    async def execute(self, context: PipelineContext) -> StageResult:
        config = context.get_stage_config(self.name)
        content: StructuredContent | None = context.get("content")
        if content is None:
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error="No content in context",
            )

        settings = get_settings()
        media_dir = settings.media_dir / "audio"
        media_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. Prepare TTS text
            tts_text = content.tts_script
            if not tts_text:
                # Fallback: join section tts_scripts or body text
                parts = []
                for sec in content.sections:
                    parts.append(sec.tts_script or sec.body)
                tts_text = "\n\n".join(parts)

            # 2. Apply pronunciation corrections
            domains = [content.domain.value]
            tts_text = apply_pronunciation(tts_text, domains)
            tts_text = format_numbers_for_speech(tts_text)

            # 3. Generate SSML
            scene = determine_scene(content.domain.value, content.content_layer.value)
            scene_override = config.get("style", scene)
            ssml = text_to_ssml(tts_text, scene=scene_override)

            # 4. Get voice config from account
            from src.core.config import get_account_config
            account_config = get_account_config(content.account_id)
            voice_id = account_config.get("voice", {}).get("voice_id", "")
            voice_id = config.get("voice_id", voice_id)

            # 5. Synthesize
            provider = get_tts_provider()
            speed = config.get("speed", 1.0)
            if isinstance(speed, str):
                speed_map = {"slow": 0.85, "moderate": 0.95, "normal": 1.0, "fast": 1.1}
                speed = speed_map.get(speed, 1.0)

            request = TTSRequest(
                text=tts_text,
                ssml=ssml,
                voice_id=voice_id,
                speed=speed,
                output_format="mp3",
            )

            response = await provider.synthesize(request)

            if not response.audio_data:
                return StageResult(
                    stage_name=self.name,
                    status=PipelineStatus.FAILED,
                    error="TTS returned empty audio",
                )

            # 6. Save raw audio
            audio_id = uuid4()
            raw_path = media_dir / f"{audio_id}_raw.mp3"
            raw_path.write_bytes(response.audio_data)

            # 7. Post-process
            processor = AudioPostProcessor(
                target_lufs=-16.0 if content.content_layer.value == "value" else -14.0,
                scene=scene_override,
            )
            processed_path = media_dir / f"{audio_id}_processed.mp3"
            processed_path = await processor.process(raw_path, processed_path)

            # 8. Mix BGM (optional)
            final_path = processed_path
            bgm_path = select_bgm(
                domain=content.domain.value,
                layer=content.content_layer.value,
            )
            if bgm_path:
                mixed_path = media_dir / f"{audio_id}_final.mp3"
                final_path = await mix_bgm(processed_path, bgm_path, mixed_path)

            # 9. Quality check
            quality = await check_audio_quality(final_path, tts_text)

            # 10. Build AudioAsset
            audio_asset = AudioAsset(
                id=audio_id,
                content_id=content.id,
                file_path=str(final_path),
                format="mp3",
                duration=response.duration,
                quality_score=10.0 if quality["passed"] else 5.0,
            )

            # Store in context
            context.set("audio", audio_asset)
            context.run.audio = audio_asset

            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.COMPLETED,
                output={
                    "audio_path": str(final_path),
                    "duration": response.duration,
                    "quality_passed": quality["passed"],
                    "provider": provider.name,
                    "scene": scene_override,
                    "has_bgm": bgm_path is not None,
                },
            )

        except Exception as e:
            logger.exception("tts_engine.failed")
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error=str(e),
            )
