"""Trending topics aggregation from multiple sources."""
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

# Multiple DailyHot-compatible API endpoints to try (instances go up/down)
DAILYHOT_ENDPOINTS = [
    "https://dailyhot.hkg1.zeabur.app",
    "https://hot.imsyy.top",
    "https://dailyhot-api.vercel.app",
]

# Fallback: Baidu hot search RSS (always available)
BAIDU_HOT_URL = "https://top.baidu.com/board?tab=realtime"


async def fetch_trending(
    base_url: str = "",
    platforms: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch trending topics from DailyHot API.

    Tries multiple endpoints. Falls back to direct RSS/API if all fail.
    Returns a list of dicts with keys: title, url, hot_score, platform, desc
    """
    if platforms is None:
        platforms = PLATFORM_MAPPING["general"]

    # Try DailyHot endpoints
    endpoints = [base_url] if base_url else DAILYHOT_ENDPOINTS
    for endpoint in endpoints:
        if not endpoint:
            continue
        results = await _fetch_from_dailyhot(endpoint, platforms)
        if results:
            return results

    # All DailyHot instances failed — use fallback sources
    logger.warning("dailyhot.all_endpoints_failed, using fallback")
    return await _fallback_trending(platforms)


async def fetch_domain_trending(
    domain: str,
    base_url: str = "",
) -> list[dict[str, Any]]:
    """Fetch trending topics for a specific content domain."""
    platforms = PLATFORM_MAPPING.get(domain, PLATFORM_MAPPING["general"])
    return await fetch_trending(base_url=base_url, platforms=platforms)


async def _fetch_from_dailyhot(
    base_url: str,
    platforms: list[str],
) -> list[dict[str, Any]]:
    """Try to fetch from a single DailyHot endpoint."""
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for platform in platforms:
            for path_pattern in [f"/api/{platform}", f"/{platform}"]:
                try:
                    resp = await client.get(f"{base_url}{path_pattern}")
                    if resp.status_code != 200:
                        continue
                    ct = resp.headers.get("content-type", "")
                    if "json" not in ct and "javascript" not in ct:
                        continue
                    data = resp.json()
                    items = data.get("data", [])
                    if not items:
                        continue
                    for item in items[:20]:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "hot_score": item.get("hot", 0),
                            "platform": platform,
                            "desc": item.get("desc", ""),
                            "mobile_url": item.get("mobileUrl", ""),
                        })
                    break  # This path pattern worked for this platform
                except Exception:
                    continue

    results.sort(key=lambda x: x.get("hot_score", 0), reverse=True)
    return results


async def _fallback_trending(platforms: list[str]) -> list[dict[str, Any]]:
    """Fallback: fetch trending from direct sources when DailyHot is down."""
    results: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        # Zhihu hot list API (usually available)
        if any(p in platforms for p in ["zhihu", "general"]):
            try:
                resp = await client.get(
                    "https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", [])[:15]:
                        target = item.get("target", {})
                        results.append({
                            "title": target.get("title", ""),
                            "url": f"https://www.zhihu.com/question/{target.get('id', '')}",
                            "hot_score": item.get("detail_text", "0").replace("万热度", "0000").replace(" 热度", ""),
                            "platform": "zhihu",
                            "desc": target.get("excerpt", ""),
                        })
            except Exception:
                logger.debug("fallback.zhihu_failed")

        # Weibo hot search API
        if any(p in platforms for p in ["weibo", "general"]):
            try:
                resp = await client.get(
                    "https://weibo.com/ajax/side/hotSearch",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("data", {}).get("realtime", [])[:15]:
                        results.append({
                            "title": item.get("word", ""),
                            "url": f"https://s.weibo.com/weibo?q={item.get('word', '')}",
                            "hot_score": item.get("num", 0),
                            "platform": "weibo",
                            "desc": item.get("label_name", ""),
                        })
            except Exception:
                logger.debug("fallback.weibo_failed")

    # If still nothing, generate minimal placeholder for pipeline to continue
    if not results:
        logger.warning("fallback.all_sources_failed, using placeholder topics")
        results = [
            {"title": "全球经济展望与投资策略", "url": "", "hot_score": 100, "platform": "manual", "desc": "每日常规选题"},
            {"title": "本周天象与能量解读", "url": "", "hot_score": 100, "platform": "manual", "desc": "每周常规选题"},
            {"title": "国际局势深度分析", "url": "", "hot_score": 100, "platform": "manual", "desc": "每周常规选题"},
        ]

    results.sort(key=lambda x: x.get("hot_score", 0) if isinstance(x.get("hot_score"), (int, float)) else 0, reverse=True)
    return results
