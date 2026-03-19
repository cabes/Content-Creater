"""Astrology chart and mystical symbol generation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


async def generate_natal_chart(
    date_str: str = "",
    location: str = "",
    output_dir: Path | None = None,
) -> Path | None:
    """Generate an astrological natal chart SVG/PNG."""
    try:
        from kerykeion import AstrologicalSubject, KerykeionChartSVG
    except ImportError:
        logger.warning("kerykeion not installed, generating placeholder chart")
        return await _generate_placeholder_chart(output_dir, "Natal Chart")

    if output_dir is None:
        from src.core.config import get_settings
        output_dir = get_settings().media_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Parse date
        from datetime import datetime
        if date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            dt = datetime.now()

        subject = AstrologicalSubject(
            "Chart",
            dt.year, dt.month, dt.day,
            12, 0,  # noon if no time specified
            lng=116.4, lat=39.9,  # Default: Beijing
        )

        chart = KerykeionChartSVG(subject)
        svg_path = output_dir / f"natal_chart_{dt.strftime('%Y%m%d')}.svg"
        chart.makeSVG(str(svg_path))

        logger.info("astrology.natal_chart_generated", path=str(svg_path))
        return svg_path

    except Exception as e:
        logger.warning("astrology.chart_failed", error=str(e))
        return await _generate_placeholder_chart(output_dir, "Natal Chart")


async def generate_zodiac_symbol(
    sign: str,
    output_dir: Path | None = None,
    size: int = 512,
) -> Path | None:
    """Generate a zodiac symbol image."""
    # Unicode zodiac symbols
    zodiac_symbols = {
        "aries": "♈", "taurus": "♉", "gemini": "♊", "cancer": "♋",
        "leo": "♌", "virgo": "♍", "libra": "♎", "scorpio": "♏",
        "sagittarius": "♐", "capricorn": "♑", "aquarius": "♒", "pisces": "♓",
    }

    symbol = zodiac_symbols.get(sign.lower(), "☉")
    return await _generate_symbol_image(symbol, sign, output_dir, size)


async def _generate_placeholder_chart(output_dir: Path | None, title: str) -> Path | None:
    """Generate a placeholder chart image."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return None

    if output_dir is None:
        from src.core.config import get_settings
        output_dir = get_settings().media_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 10))
    fig.set_facecolor("#0a0a1a")
    ax.set_facecolor("#0a0a1a")

    # Draw zodiac wheel
    theta = np.linspace(0, 2 * np.pi, 13)
    r = 4
    ax.plot(r * np.cos(theta), r * np.sin(theta), color="#ffd700", linewidth=2)

    # Inner circle
    r2 = 2.5
    ax.plot(r2 * np.cos(theta), r2 * np.sin(theta), color="#9b59b6", linewidth=1)

    # Zodiac symbols
    symbols = "♈♉♊♋♌♍♎♏♐♑♒♓"
    for i, sym in enumerate(symbols):
        angle = 2 * np.pi * i / 12 + np.pi / 12
        x = 3.25 * np.cos(angle)
        y = 3.25 * np.sin(angle)
        ax.text(x, y, sym, fontsize=20, ha="center", va="center", color="#ffd700")

    ax.set_xlim(-5, 5)
    ax.set_ylim(-5, 5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=18, color="#ffd700", pad=20)

    import uuid
    output_path = output_dir / f"chart_{uuid.uuid4().hex[:8]}.png"
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    return output_path


async def _generate_symbol_image(
    symbol: str,
    name: str,
    output_dir: Path | None,
    size: int = 512,
) -> Path | None:
    """Generate a symbol as a styled image."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    if output_dir is None:
        from src.core.config import get_settings
        output_dir = get_settings().media_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(size / 100, size / 100))
    fig.set_facecolor("#0a0a1a")
    ax.text(0.5, 0.5, symbol, fontsize=80, ha="center", va="center",
            color="#ffd700", transform=ax.transAxes)
    ax.axis("off")

    import uuid
    output_path = output_dir / f"symbol_{name}_{uuid.uuid4().hex[:8]}.png"
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close()
    return output_path
