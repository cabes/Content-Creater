"""Camera movement system for video scenes."""
from __future__ import annotations

from typing import Any, Callable


def get_camera_effect(
    move: str,
    duration: float,
    intensity: float = 0.05,
) -> Callable[[float], float] | None:
    """Get a resize function for camera movement simulation.

    Returns a function f(t) -> scale_factor for use with moviepy resize.
    """
    if move == "push_in":
        return lambda t: 1 + intensity * (t / duration)
    elif move == "pull_out":
        return lambda t: (1 + intensity) - intensity * (t / duration)
    elif move == "zoom_focus":
        # Zoom in then stabilize
        mid = duration / 2
        return lambda t: 1 + intensity * min(t / mid, 1.0)
    elif move == "static":
        return None
    else:
        return None


# Pan effects need position functions instead of resize
def get_pan_effect(
    move: str,
    size: tuple[int, int],
    duration: float,
    pan_distance: int = 100,
) -> Callable[[float], tuple[int, int]] | None:
    """Get a position function for panning effects.

    Returns a function f(t) -> (x, y) position.
    """
    cx, cy = size[0] // 2, size[1] // 2

    if move == "pan_left":
        return lambda t: (cx + int(pan_distance * (0.5 - t / duration)), cy)
    elif move == "pan_right":
        return lambda t: (cx - int(pan_distance * (0.5 - t / duration)), cy)
    elif move == "pan_up":
        return lambda t: (cx, cy + int(pan_distance * (0.5 - t / duration)))
    elif move == "pan_down":
        return lambda t: (cx, cy - int(pan_distance * (0.5 - t / duration)))
    else:
        return None
