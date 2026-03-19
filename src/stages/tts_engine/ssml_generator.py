"""Convert emotion-annotated text to SSML for fine-grained TTS control."""
from __future__ import annotations

import re
from typing import Any

from src.core.models import EmotionType

# Emotion to SSML prosody mapping
EMOTION_PROSODY: dict[str, dict[str, Any]] = {
    EmotionType.EXCITED.value: {"rate": "105%", "pitch": "+2st", "emphasis": "strong"},
    EmotionType.SERIOUS.value: {"rate": "95%", "pitch": "-2st", "emphasis": "moderate"},
    EmotionType.TENSE.value: {"rate": "90%", "pitch": "-3st", "emphasis": "moderate"},
    EmotionType.ANALYTICAL.value: {"rate": "92%", "pitch": "-1st", "emphasis": "none"},
    EmotionType.MYSTICAL.value: {"rate": "85%", "pitch": "-4st", "emphasis": "moderate"},
    EmotionType.MEDITATIVE.value: {"rate": "70%", "pitch": "-5st", "emphasis": "reduced"},
    EmotionType.SOLEMN.value: {"rate": "88%", "pitch": "-3st", "emphasis": "strong"},
    EmotionType.HUMOROUS.value: {"rate": "108%", "pitch": "+1st", "emphasis": "moderate"},
    EmotionType.WARM.value: {"rate": "95%", "pitch": "+0st", "emphasis": "moderate"},
    EmotionType.URGENT.value: {"rate": "110%", "pitch": "+1st", "emphasis": "strong"},
}

# Scene profiles for overall speech style
SCENE_PROFILES = {
    "finance_news": {"base_rate": "110%", "base_pitch": "+1st", "break_style": "short"},
    "deep_analysis": {"base_rate": "95%", "base_pitch": "+0st", "break_style": "medium"},
    "geopolitics": {"base_rate": "100%", "base_pitch": "-1st", "break_style": "medium"},
    "mystical_reading": {"base_rate": "85%", "base_pitch": "-4st", "break_style": "long"},
    "meditation_guide": {"base_rate": "70%", "base_pitch": "-5st", "break_style": "very_long"},
    "hot_take": {"base_rate": "115%", "base_pitch": "+2st", "break_style": "short"},
    "fear_warning": {"base_rate": "90%", "base_pitch": "-2st", "break_style": "medium"},
    "inspirational": {"base_rate": "105%", "base_pitch": "+1st", "break_style": "medium"},
}

BREAK_DURATIONS = {
    "short": {"sentence": "300ms", "paragraph": "800ms"},
    "medium": {"sentence": "500ms", "paragraph": "1200ms"},
    "long": {"sentence": "800ms", "paragraph": "2000ms"},
    "very_long": {"sentence": "1500ms", "paragraph": "4000ms"},
}

# Regex patterns
EMOTION_PATTERN = re.compile(r'\[emotion:(\w+)\](.*?)\[/emotion\]', re.DOTALL)
PAUSE_PATTERN = re.compile(r'\[pause:([\d.]+)s?\]')


def text_to_ssml(
    text: str,
    scene: str = "deep_analysis",
    voice_id: str = "",
) -> str:
    """Convert emotion-annotated text to SSML.

    Input markers:
      [emotion:excited]text[/emotion]
      [pause:1.5s]
    """
    profile = SCENE_PROFILES.get(scene, SCENE_PROFILES["deep_analysis"])
    break_style = profile.get("break_style", "medium")
    breaks = BREAK_DURATIONS[break_style]

    ssml_parts = ['<speak>']

    # Apply base prosody
    ssml_parts.append(f'<prosody rate="{profile["base_rate"]}" pitch="{profile["base_pitch"]}">')

    # Process text segment by segment
    remaining = text
    last_end = 0

    # Find all markers and process in order
    markers = []
    for m in EMOTION_PATTERN.finditer(text):
        markers.append(("emotion", m.start(), m.end(), m.group(1), m.group(2)))
    for m in PAUSE_PATTERN.finditer(text):
        markers.append(("pause", m.start(), m.end(), m.group(1), ""))

    markers.sort(key=lambda x: x[1])

    for marker_type, start, end, param, content in markers:
        # Add plain text before this marker
        if start > last_end:
            plain = text[last_end:start].strip()
            if plain:
                ssml_parts.append(_add_sentence_breaks(plain, breaks))

        if marker_type == "emotion":
            prosody = EMOTION_PROSODY.get(param, {})
            if prosody:
                attrs = []
                if prosody.get("rate"):
                    attrs.append(f'rate="{prosody["rate"]}"')
                if prosody.get("pitch"):
                    attrs.append(f'pitch="{prosody["pitch"]}"')
                attr_str = " ".join(attrs)

                emphasis = prosody.get("emphasis", "none")
                if emphasis and emphasis != "none":
                    ssml_parts.append(f'<prosody {attr_str}><emphasis level="{emphasis}">{content.strip()}</emphasis></prosody>')
                else:
                    ssml_parts.append(f'<prosody {attr_str}>{content.strip()}</prosody>')
            else:
                ssml_parts.append(content.strip())

        elif marker_type == "pause":
            duration_s = float(param)
            ssml_parts.append(f'<break time="{int(duration_s * 1000)}ms"/>')

        last_end = end

    # Add remaining text
    if last_end < len(text):
        remaining_text = text[last_end:].strip()
        if remaining_text:
            ssml_parts.append(_add_sentence_breaks(remaining_text, breaks))

    ssml_parts.append('</prosody>')
    ssml_parts.append('</speak>')

    return "\n".join(ssml_parts)


def _add_sentence_breaks(text: str, breaks: dict[str, str]) -> str:
    """Add break tags after sentence-ending punctuation."""
    result = text
    for punct in ['。', '！', '？', '；']:
        result = result.replace(punct, f'{punct}<break time="{breaks["sentence"]}"/>')
    # Paragraph breaks
    result = result.replace('\n\n', f'\n<break time="{breaks["paragraph"]}"/>\n')
    return result


def determine_scene(domain: str, content_layer: str, emotion: str = "") -> str:
    """Determine the scene profile based on content attributes."""
    scene_map = {
        ("finance", "hook"): "finance_news",
        ("finance", "value"): "deep_analysis",
        ("geopolitics", "hook"): "geopolitics",
        ("geopolitics", "value"): "deep_analysis",
        ("mystical", "hook"): "mystical_reading",
        ("mystical", "value"): "mystical_reading",
        ("knowledge", "hook"): "hot_take",
        ("knowledge", "value"): "deep_analysis",
    }
    return scene_map.get((domain, content_layer), "deep_analysis")
