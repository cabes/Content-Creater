"""BGM selection and ducking mixer."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
import yaml

from src.core.config import CONFIG_DIR

logger = structlog.get_logger()


def select_bgm(
    domain: str,
    layer: str = "hook",
    emotion: str = "",
    energy_curve: str = "neutral",
) -> Path | None:
    """Select appropriate BGM track based on domain × layer × emotion."""
    # Try to load mapping config
    mapping_path = CONFIG_DIR / "audio" / "bgm_mapping.yaml"
    if mapping_path.exists():
        with open(mapping_path) as f:
            mapping = yaml.safe_load(f) or {}
    else:
        mapping = {}

    # Try domain-specific directory
    bgm_dir = CONFIG_DIR / "audio" / "bgm"
    candidates = []

    # Check domain-specific directory
    domain_dir = bgm_dir / domain
    if domain_dir.exists():
        candidates = list(domain_dir.glob("*.mp3")) + list(domain_dir.glob("*.wav"))

    # Fallback to hooks/general directory
    if not candidates:
        layer_dir = bgm_dir / ("hooks" if layer == "hook" else "transitions")
        if layer_dir.exists():
            candidates = list(layer_dir.glob("*.mp3")) + list(layer_dir.glob("*.wav"))

    if not candidates:
        return None

    # Simple selection (could be more sophisticated with emotion matching)
    import random
    return random.choice(candidates)


async def mix_bgm(
    voice_path: Path,
    bgm_path: Path,
    output_path: Path,
    voice_volume: float = 0.0,  # dB adjustment
    bgm_volume_normal: float = -18.0,  # dB when voice is active
    bgm_volume_pause: float = -8.0,  # dB during pauses
    fade_in_ms: int = 2000,
    fade_out_ms: int = 3000,
) -> Path:
    """Mix BGM with voice audio, applying ducking."""
    try:
        from pydub import AudioSegment

        voice = AudioSegment.from_file(str(voice_path))
        bgm = AudioSegment.from_file(str(bgm_path))

        # Loop BGM to match voice duration (+fade out buffer)
        target_duration = len(voice) + fade_out_ms + 1000
        if len(bgm) < target_duration:
            loops_needed = (target_duration // len(bgm)) + 1
            bgm = bgm * loops_needed
        bgm = bgm[:target_duration]

        # Apply fade in/out
        bgm = bgm.fade_in(fade_in_ms).fade_out(fade_out_ms)

        # Apply ducking: lower BGM during voice, raise during silence
        # Simple approach: set BGM to low level throughout (voice always present)
        bgm = bgm + bgm_volume_normal  # Set to ducked level

        # Overlay
        if voice_volume != 0:
            voice = voice + voice_volume
        mixed = voice.overlay(bgm)

        mixed.export(str(output_path), format=output_path.suffix.lstrip("."))
        logger.info("bgm_mixer.done", duration=len(mixed)/1000)
        return output_path

    except ImportError:
        logger.warning("pydub not installed, returning voice-only audio")
        import shutil
        shutil.copy2(voice_path, output_path)
        return output_path
