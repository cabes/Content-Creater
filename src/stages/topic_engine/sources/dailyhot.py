"""DailyHot aggregated trending topics source."""
from __future__ import annotations

from typing import Any

import httpx
import structlog

logger = structlog.get_logger()

# DailyHot platform IDs for different domains
PLATFORM_MAPPING = {
    "finance": ["eastmoney", "xueqiu", "wallstreetcn", "cls"],
    "geopolitics": ["thepaper", "guancha", "bbc", "zaobao"],
    "knowledge": ["zhihu", "bilibili", "weibo"],
    "mystical": ["weibo", "xiaohongshu", "zhihu"],
    "general": ["weibo", "zhihu", "douyin", "toutiao", "baidu"],
}


async def fetch_trending(
    base_url: str = "https://dailyhot.hkg1.zeabur.app",
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch trending topics from DailyHot API.

    Returns a list of dicts with keys: title, url, hot_score, platform, desc
    """
    if platforms is None:
        platforms = PLATFORM_MAPPING["general"]

    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for platform in platforms:
            try:
                resp = await client.get(f"{base_url}/api/{platform}")
                if resp.status_code != 200:
                    logger.warning("dailyhot.fetch_failed", platform=platform, status=resp.status_code)
                    continue
                data = resp.json()
                items = data.get("data", [])
                for item in items[:20]:  # Top 20 per platform
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "hot_score": item.get("hot", 0),
                        "platform": platform,
                        "desc": item.get("desc", ""),
                        "mobile_url": item.get("mobileUrl", ""),
                    })
            except Exception:
                logger.exception("dailyhot.error", platform=platform)

    # Sort by hot score descending
    results.sort(key=lambda x: x.get("hot_score", 0), reverse=True)
    return results


async def fetch_domain_trending(
    domain: str,
    base_url: str = "https://dailyhot.hkg1.zeabur.app",
) -> list[dict[str, Any]]:
    """Fetch trending topics for a specific content domain."""
    platforms = PLATFORM_MAPPING.get(domain, PLATFORM_MAPPING["general"])
    return await fetch_trending(base_url=base_url, platforms=platforms)
