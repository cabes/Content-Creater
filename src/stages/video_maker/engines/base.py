"""Abstract base class for video rendering engines."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.core.models import Scene, Storyboard


class BaseVideoEngine(ABC):
    """Abstract base for video rendering engines."""

    name: str = "base"

    def __init__(self, output_dir: Path | None = None, **kwargs: Any):
        self.output_dir = output_dir or Path("media/video")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.extra = kwargs

    @abstractmethod
    async def render_scene(self, scene: Scene, assets: dict[str, Path]) -> Path:
        """Render a single scene to a video clip."""
        ...

    @abstractmethod
    async def render_storyboard(
        self,
        storyboard: Storyboard,
        assets: dict[str, Path],
        audio_path: Path | None = None,
    ) -> Path:
        """Render a complete storyboard to final video."""
        ...

    def supports_scene_type(self, scene_type: str) -> bool:
        """Check if this engine supports a given scene type."""
        return True
