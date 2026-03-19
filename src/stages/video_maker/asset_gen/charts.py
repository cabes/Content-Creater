"""Dynamic chart generation using matplotlib."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


async def generate_chart(
    chart_type: str,
    data: dict[str, Any],
    output_dir: Path,
    width: int = 1920,
    height: int = 1080,
    style: str = "dark_background",
) -> Path | None:
    """Generate a chart image using matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
    except ImportError:
        logger.warning("matplotlib not installed")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    plt.style.use(style)

    title = data.get("title", "Chart")

    try:
        if chart_type == "bar":
            labels = data.get("labels", [])
            values = data.get("values", [])
            colors = data.get("colors", None)
            ax.bar(labels, values, color=colors)
            ax.set_title(title, fontsize=20, pad=20)

        elif chart_type == "line":
            for series in data.get("series", []):
                ax.plot(
                    series.get("x", []),
                    series.get("y", []),
                    label=series.get("label", ""),
                    linewidth=2,
                )
            ax.legend(fontsize=12)
            ax.set_title(title, fontsize=20, pad=20)

        elif chart_type == "pie":
            labels = data.get("labels", [])
            values = data.get("values", [])
            ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.set_title(title, fontsize=20, pad=20)

        elif chart_type == "comparison":
            # Side-by-side comparison
            categories = data.get("categories", [])
            series_a = data.get("series_a", [])
            series_b = data.get("series_b", [])
            import numpy as np
            x = np.arange(len(categories))
            w = 0.35
            ax.bar(x - w / 2, series_a, w, label=data.get("label_a", "A"))
            ax.bar(x + w / 2, series_b, w, label=data.get("label_b", "B"))
            ax.set_xticks(x)
            ax.set_xticklabels(categories)
            ax.legend()
            ax.set_title(title, fontsize=20, pad=20)

        else:
            logger.warning("chart.unknown_type", chart_type=chart_type)
            plt.close()
            return None

        # Style adjustments
        ax.tick_params(labelsize=12)
        plt.tight_layout()

        # Save
        import uuid
        output_path = output_dir / f"chart_{uuid.uuid4().hex[:8]}.png"
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor(), edgecolor="none")
        plt.close()

        logger.info("chart.generated", type=chart_type, path=str(output_path))
        return output_path

    except Exception as e:
        plt.close()
        logger.exception("chart.generation_failed")
        return None
