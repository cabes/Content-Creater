"""Map visualization for geopolitics content."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


async def generate_map(
    regions: list[str] | None = None,
    highlights: dict[str, str] | None = None,
    output_dir: Path | None = None,
    title: str = "",
    style: str = "dark",
) -> Path | None:
    """Generate a map visualization highlighting specific regions."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not installed")
        return None

    if output_dir is None:
        from src.core.config import get_settings
        output_dir = get_settings().media_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Try geopandas for real map visualization
        import geopandas as gpd

        world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))

        fig, ax = plt.subplots(1, 1, figsize=(19.2, 10.8))

        if style == "dark":
            fig.set_facecolor("#1a1a2e")
            ax.set_facecolor("#1a1a2e")
            base_color = "#2d2d44"
            border_color = "#444466"
        else:
            base_color = "#e0e0e0"
            border_color = "#999999"

        world.plot(ax=ax, color=base_color, edgecolor=border_color, linewidth=0.5)

        if highlights:
            for country_name, color in highlights.items():
                country = world[world.name == country_name]
                if not country.empty:
                    country.plot(ax=ax, color=color, edgecolor="white", linewidth=1)

        ax.set_xlim([-180, 180])
        ax.set_ylim([-60, 85])
        ax.axis("off")

        if title:
            ax.set_title(title, fontsize=20, color="white" if style == "dark" else "black", pad=20)

        import uuid
        output_path = output_dir / f"map_{uuid.uuid4().hex[:8]}.png"
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close()

        logger.info("map.generated", path=str(output_path))
        return output_path

    except ImportError:
        # Fallback: generate a placeholder
        fig, ax = plt.subplots(figsize=(19.2, 10.8))
        ax.text(0.5, 0.5, f"🗺️ {title or 'Map'}\n(geopandas needed for real maps)",
                ha="center", va="center", fontsize=24, transform=ax.transAxes)
        ax.set_facecolor("#1a1a2e")
        ax.axis("off")

        import uuid
        output_path = output_dir / f"map_placeholder_{uuid.uuid4().hex[:8]}.png"
        fig.savefig(str(output_path), dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close()
        return output_path
