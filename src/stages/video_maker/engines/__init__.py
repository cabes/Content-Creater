"""Video engine registry and factory."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseVideoEngine
from .moviepy_engine import MoviePyEngine
from .remotion import RemotionEngine
from .manim_engine import ManimEngine
from .mystical_engine import MysticalEngine

__all__ = ["BaseVideoEngine", "get_video_engine"]

_ENGINES: dict[str, type[BaseVideoEngine]] = {
    "moviepy": MoviePyEngine,
    "remotion": RemotionEngine,
    "manim": ManimEngine,
    "mystical": MysticalEngine,
}


def get_video_engine(
    engine_name: str = "moviepy",
    output_dir: Path | None = None,
    **kwargs: Any,
) -> BaseVideoEngine:
    """Factory: create a video engine by name."""
    cls = _ENGINES.get(engine_name)
    if cls is None:
        # Fallback to MoviePy
        cls = MoviePyEngine
    return cls(output_dir=output_dir, **kwargs)
