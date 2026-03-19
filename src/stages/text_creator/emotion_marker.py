"""Emotion markup processing for TTS and visual synchronization."""
from __future__ import annotations

import re

from src.core.models import EmotionMarker, EmotionType

# Pattern: [emotion:type]text[/emotion]
EMOTION_PATTERN = re.compile(
    r'\[emotion:(\w+)\](.*?)\[/emotion\]',
    re.DOTALL,
)


def extract_emotion_markers(text: str) -> list[EmotionMarker]:
    """Extract emotion markers from annotated text."""
    markers = []
    for match in EMOTION_PATTERN.finditer(text):
        emotion_str = match.group(1)
        content = match.group(2)
        try:
            emotion = EmotionType(emotion_str)
        except ValueError:
            emotion = EmotionType.ANALYTICAL  # fallback

        markers.append(EmotionMarker(
            emotion=emotion,
            text=content,
            start_pos=match.start(),
            end_pos=match.end(),
        ))
    return markers


def strip_emotion_markers(text: str) -> str:
    """Remove emotion markup, keeping only the text content."""
    return EMOTION_PATTERN.sub(r'\2', text)


def add_pause_markers(text: str) -> str:
    """Add pause markers at natural break points for TTS."""
    # Add pauses after key punctuation
    text = re.sub(r'([。！？])\s*', r'\1[pause:0.5s]', text)
    # Add longer pauses at paragraph breaks
    text = re.sub(r'\n\n+', '\n\n[pause:1.5s]\n\n', text)
    return text
