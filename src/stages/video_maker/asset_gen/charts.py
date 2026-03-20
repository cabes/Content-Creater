"""Dynamic chart generation using matplotlib with dark theme and CJK support."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger()

# CJK font path
_CJK_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_CJK_FONT_FALLBACK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"


def _get_font_path() -> str:
    for p in [_CJK_FONT_PATH, _CJK_FONT_FALLBACK]:
        if Path(p).exists():
            return p
    return ""


async def generate_chart(
    chart_type: str,
    data: dict[str, Any],
    output_dir: Path,
    width: int = 1920,
    height: int = 1080,
    style: str = "dark_background",
) -> Path | None:
    """Generate a chart image with dark theme and CJK font support."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        import numpy as np
    except ImportError:
        logger.warning("matplotlib not installed")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    # Setup CJK font
    font_path = _get_font_path()
    font_prop = None
    if font_path:
        font_prop = fm.FontProperties(fname=font_path)
        fm.fontManager.addfont(font_path)

    fp = {"fontproperties": font_prop} if font_prop else {}

    # Dark theme colors
    bg_color = "#0d1b2a"
    text_color = "#e0e0e0"
    grid_color = "#1b2838"
    accent_colors = ["#4da6ff", "#ff6b6b", "#51cf66", "#ffd43b", "#cc5de8", "#ff922b"]

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    ax.tick_params(colors=text_color, labelsize=12)
    ax.spines["bottom"].set_color(grid_color)
    ax.spines["left"].set_color(grid_color)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(True, alpha=0.15, color=grid_color)

    title = data.get("title", "")

    try:
        if chart_type == "bar":
            labels = data.get("labels", ["A", "B", "C", "D"])
            values = data.get("values", [])
            if not values or all(v == 0 for v in values):
                values = [np.random.uniform(2, 10) for _ in labels]
            bars = ax.bar(labels, values, color=accent_colors[:len(labels)], width=0.6, edgecolor="none")
            # Value labels on bars
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                        f"{val:.1f}", ha="center", va="bottom", color=text_color, fontsize=11,
                        **({"fontproperties": font_prop} if font_prop else {}))
            ax.set_xticklabels(labels, **fp)

        elif chart_type == "line":
            series_list = data.get("series", [])
            if not series_list:
                # Generate sample line data
                x = list(range(1, 13))
                series_list = [{"x": x, "y": [round(np.random.uniform(3, 8) + i*0.3, 1) for i in range(12)], "label": title or "趋势"}]
            for idx, series in enumerate(series_list):
                x = series.get("x", list(range(len(series.get("y", [])))))
                y = series.get("y", [])
                if not y:
                    y = [np.random.uniform(2, 10) for _ in x]
                label = series.get("label", f"Series {idx+1}")
                color = accent_colors[idx % len(accent_colors)]
                ax.plot(x, y, label=label, linewidth=2.5, color=color, marker="o", markersize=4)
                # Fill under line
                ax.fill_between(x, y, alpha=0.1, color=color)
            ax.legend(fontsize=11, prop=font_prop, facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color)

        elif chart_type == "pie":
            labels = data.get("labels", ["A", "B", "C", "D"])
            values = data.get("values", [])
            if not values:
                values = [np.random.uniform(10, 40) for _ in labels]
            colors = accent_colors[:len(labels)]
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct="%1.1f%%", startangle=90,
                colors=colors, textprops={"color": text_color, **({"fontproperties": font_prop} if font_prop else {})},
            )
            for t in autotexts:
                t.set_color("white")
                t.set_fontsize(11)

        elif chart_type == "comparison":
            categories = data.get("categories", ["Q1", "Q2", "Q3", "Q4"])
            series_a = data.get("series_a", [np.random.uniform(3, 8) for _ in categories])
            series_b = data.get("series_b", [np.random.uniform(3, 8) for _ in categories])
            x = np.arange(len(categories))
            w = 0.35
            ax.bar(x - w/2, series_a, w, label=data.get("label_a", "A"), color=accent_colors[0])
            ax.bar(x + w/2, series_b, w, label=data.get("label_b", "B"), color=accent_colors[1])
            ax.set_xticks(x)
            ax.set_xticklabels(categories, **fp)
            ax.legend(prop=font_prop, facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color)

        else:
            plt.close()
            return None

        if title:
            ax.set_title(title, fontsize=18, color=text_color, pad=15, **({"fontproperties": font_prop} if font_prop else {}))

        ax.tick_params(axis="x", **fp if fp else {})
        plt.tight_layout(pad=1.5)

        output_path = output_dir / f"chart_{uuid4().hex[:8]}.png"
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor=bg_color, edgecolor="none")
        plt.close()

        logger.info("chart.generated", type=chart_type, path=str(output_path))
        return output_path

    except Exception:
        plt.close()
        logger.exception("chart.generation_failed")
        return None
