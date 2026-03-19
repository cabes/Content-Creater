"""Multi-domain pronunciation dictionary management."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.core.config import CONFIG_DIR

# In-memory pronunciation dictionaries
_DICTS: dict[str, dict[str, str]] = {}


def load_pronunciation_dict(domain: str) -> dict[str, str]:
    """Load pronunciation dictionary for a domain."""
    if domain in _DICTS:
        return _DICTS[domain]

    result: dict[str, str] = {}
    path = CONFIG_DIR / "pronunciation" / f"{domain}.dict"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                result[parts[0]] = parts[1]

    _DICTS[domain] = result
    return result


def apply_pronunciation(text: str, domains: list[str] | None = None) -> str:
    """Apply pronunciation corrections to text.

    Replaces terms with their phonetic-friendly versions for TTS.
    """
    if domains is None:
        domains = ["finance", "geopolitics", "military", "mystical"]

    for domain in domains:
        pdict = load_pronunciation_dict(domain)
        for term, replacement in pdict.items():
            text = text.replace(term, replacement)

    return text


def format_numbers_for_speech(text: str) -> str:
    """Convert numbers to speech-friendly format."""
    # Percentages: 3.5% -> 百分之三点五
    def pct_replace(m: re.Match) -> str:
        num = m.group(1)
        return f"百分之{_num_to_chinese(num)}"
    text = re.sub(r'(\d+\.?\d*)%', pct_replace, text)

    # Currency: $100 -> 100美元, ¥500 -> 500元
    text = re.sub(r'\$(\d[\d,]*\.?\d*)', lambda m: f"{m.group(1).replace(',','')}美元", text)
    text = re.sub(r'¥(\d[\d,]*\.?\d*)', lambda m: f"{m.group(1).replace(',','')}元", text)

    # Large numbers: 1,000,000 -> 一百万
    text = re.sub(r'(\d{1,3}(?:,\d{3})+)', lambda m: m.group(0).replace(',', ''), text)

    return text


def _num_to_chinese(num_str: str) -> str:
    """Simple number to Chinese conversion for speech."""
    mapping = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
               "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
               ".": "点"}
    return "".join(mapping.get(c, c) for c in num_str)
