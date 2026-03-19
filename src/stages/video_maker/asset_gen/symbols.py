"""Mystical symbol SVG library management."""
from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger()

# Basic SVG templates for mystical symbols
SYMBOL_SVGS = {
    "pentagram": """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <polygon points="50,5 61,40 98,40 68,62 79,97 50,75 21,97 32,62 2,40 39,40"
    fill="none" stroke="#ffd700" stroke-width="2"/>
</svg>""",
    "tree_of_life": """<svg viewBox="0 0 100 120" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="10" r="8" fill="none" stroke="#ffd700" stroke-width="1.5"/>
  <circle cx="30" cy="30" r="8" fill="none" stroke="#9b59b6" stroke-width="1.5"/>
  <circle cx="70" cy="30" r="8" fill="none" stroke="#9b59b6" stroke-width="1.5"/>
  <circle cx="50" cy="50" r="8" fill="none" stroke="#ffd700" stroke-width="1.5"/>
  <circle cx="30" cy="70" r="8" fill="none" stroke="#9b59b6" stroke-width="1.5"/>
  <circle cx="70" cy="70" r="8" fill="none" stroke="#9b59b6" stroke-width="1.5"/>
  <circle cx="50" cy="90" r="8" fill="none" stroke="#ffd700" stroke-width="1.5"/>
  <line x1="50" y1="18" x2="30" y2="22" stroke="#666" stroke-width="1"/>
  <line x1="50" y1="18" x2="70" y2="22" stroke="#666" stroke-width="1"/>
  <line x1="30" y1="38" x2="50" y2="42" stroke="#666" stroke-width="1"/>
  <line x1="70" y1="38" x2="50" y2="42" stroke="#666" stroke-width="1"/>
  <line x1="50" y1="58" x2="30" y2="62" stroke="#666" stroke-width="1"/>
  <line x1="50" y1="58" x2="70" y2="62" stroke="#666" stroke-width="1"/>
  <line x1="30" y1="78" x2="50" y2="82" stroke="#666" stroke-width="1"/>
  <line x1="70" y1="78" x2="50" y2="82" stroke="#666" stroke-width="1"/>
</svg>""",
    "yin_yang": """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="48" fill="#1a1a2e" stroke="#ffd700" stroke-width="2"/>
  <path d="M50,2 A48,48 0 0,1 50,98 A24,24 0 0,0 50,50 A24,24 0 0,1 50,2" fill="#ffd700"/>
  <circle cx="50" cy="26" r="6" fill="#1a1a2e"/>
  <circle cx="50" cy="74" r="6" fill="#ffd700"/>
</svg>""",
    "chakra": """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="45" fill="none" stroke="#ffd700" stroke-width="1"/>
  <circle cx="50" cy="50" r="30" fill="none" stroke="#9b59b6" stroke-width="1"/>
  <circle cx="50" cy="50" r="15" fill="none" stroke="#e74c3c" stroke-width="1"/>
</svg>""",
}


def get_symbol_svg(name: str) -> str | None:
    """Get an SVG string for a named symbol."""
    return SYMBOL_SVGS.get(name)


def save_symbol(name: str, output_dir: Path) -> Path | None:
    """Save a symbol SVG to file."""
    svg = get_symbol_svg(name)
    if not svg:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.svg"
    path.write_text(svg)
    return path


def list_available_symbols() -> list[str]:
    """List all available symbol names."""
    return list(SYMBOL_SVGS.keys())
