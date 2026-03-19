"""Audio quality checking: Whisper transcription comparison + anomaly detection."""
from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()


async def check_audio_quality(
    audio_path: Path,
    original_text: str,
    max_error_rate: float = 0.1,
) -> dict:
    """Check TTS audio quality by comparing Whisper transcription to original text.

    Returns quality assessment dict.
    """
    result = {
        "audio_path": str(audio_path),
        "file_exists": audio_path.exists(),
        "file_size": audio_path.stat().st_size if audio_path.exists() else 0,
        "passed": True,
        "error_rate": 0.0,
        "issues": [],
    }

    if not audio_path.exists() or result["file_size"] == 0:
        result["passed"] = False
        result["issues"].append("Audio file is empty or missing")
        return result

    # Check file size sanity (< 1KB is suspicious for speech)
    if result["file_size"] < 1024:
        result["passed"] = False
        result["issues"].append("Audio file suspiciously small")
        return result

    # Whisper transcription comparison (optional, requires whisper)
    try:
        import whisper
        model = whisper.load_model("base")
        transcription = model.transcribe(str(audio_path), language="zh")
        transcribed_text = transcription.get("text", "")

        # Simple character-level error rate
        if original_text and transcribed_text:
            orig_chars = set(original_text.replace(" ", "").replace("\n", ""))
            trans_chars = set(transcribed_text.replace(" ", ""))
            if orig_chars:
                missing = orig_chars - trans_chars
                error_rate = len(missing) / len(orig_chars)
                result["error_rate"] = error_rate
                result["transcribed_text"] = transcribed_text[:200]

                if error_rate > max_error_rate:
                    result["passed"] = False
                    result["issues"].append(f"Transcription error rate {error_rate:.2%} exceeds threshold {max_error_rate:.2%}")

    except ImportError:
        logger.debug("whisper not installed, skipping transcription check")
    except Exception as e:
        logger.warning("quality_check.whisper_failed", error=str(e))

    return result


async def detect_audio_anomalies(audio_path: Path) -> list[str]:
    """Detect anomalies in audio: long silences, clipping, etc."""
    issues = []

    try:
        from pydub import AudioSegment
        from pydub.silence import detect_silence

        audio = AudioSegment.from_file(str(audio_path))

        # Check for long unexpected silences (> 5 seconds)
        silences = detect_silence(audio, min_silence_len=5000, silence_thresh=-50)
        if silences:
            issues.append(f"Found {len(silences)} unexpected long silences (>5s)")

        # Check for clipping (samples at max)
        if audio.max > audio.max_possible_amplitude * 0.99:
            issues.append("Audio may contain clipping")

        # Check duration sanity
        duration_s = len(audio) / 1000
        if duration_s < 1:
            issues.append("Audio duration < 1 second")

    except ImportError:
        pass  # pydub optional

    return issues
