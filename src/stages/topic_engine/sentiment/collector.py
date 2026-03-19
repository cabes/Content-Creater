"""Social media sentiment data collector."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


async def collect_comments_from_trending(
    trending_items: list[dict[str, Any]],
    max_per_topic: int = 50,
) -> list[dict[str, Any]]:
    """Collect comments/reactions for trending topics.

    In production, this would scrape platform APIs or use Playwright.
    For Phase 1, we use the topic metadata itself as sentiment proxy.
    """
    collected: list[dict[str, Any]] = []

    for item in trending_items[:10]:  # Top 10 topics
        collected.append({
            "topic": item.get("title", ""),
            "platform": item.get("platform", "unknown"),
            "hot_score": item.get("hot_score", 0),
            "desc": item.get("desc", ""),
            "sample_texts": [],  # Would contain actual comments in production
            "collected_count": 0,
        })

    return collected
