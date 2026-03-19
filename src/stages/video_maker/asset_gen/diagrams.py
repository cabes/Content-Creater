"""Diagram generation: flowcharts, architecture diagrams, mind maps."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


async def generate_flowchart(
    nodes: list[dict[str, str]],
    edges: list[tuple[str, str]],
    output_dir: Path,
    title: str = "",
) -> Path | None:
    """Generate a flowchart using graphviz."""
    try:
        import graphviz
    except ImportError:
        logger.warning("graphviz not installed")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    dot = graphviz.Digraph(comment=title)
    dot.attr(rankdir="TB", bgcolor="transparent")
    dot.attr("node", shape="box", style="rounded,filled", fillcolor="#4a90d9",
             fontcolor="white", fontsize="14")
    dot.attr("edge", color="#666666", arrowsize="0.8")

    for node in nodes:
        dot.node(node["id"], node.get("label", node["id"]))

    for src, dst in edges:
        dot.edge(src, dst)

    import uuid
    output_path = output_dir / f"flowchart_{uuid.uuid4().hex[:8]}"
    dot.render(str(output_path), format="png", cleanup=True)

    final_path = Path(f"{output_path}.png")
    if final_path.exists():
        logger.info("flowchart.generated", path=str(final_path))
        return final_path
    return None


async def generate_comparison_table(
    headers: list[str],
    rows: list[list[str]],
    output_dir: Path,
    title: str = "",
) -> Path | None:
    """Generate a comparison table as an image."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib not installed")
        return None

    output_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, max(3, len(rows) * 0.8 + 1)))
    ax.axis("off")

    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc="center",
        loc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 1.5)

    # Style header row
    for j in range(len(headers)):
        table[0, j].set_facecolor("#2c3e50")
        table[0, j].set_text_props(color="white", fontweight="bold")

    if title:
        ax.set_title(title, fontsize=16, pad=20)

    import uuid
    output_path = output_dir / f"table_{uuid.uuid4().hex[:8]}.png"
    fig.savefig(str(output_path), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()

    logger.info("table.generated", path=str(output_path))
    return output_path
