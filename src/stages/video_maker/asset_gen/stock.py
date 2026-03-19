"""Stock media retrieval from Pexels/Pixabay."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx
import structlog

logger = structlog.get_logger()


async def search_pexels(
    query: str,
    media_type: str = "photos",
    per_page: int = 5,
) -> list[dict[str, Any]]:
    """Search Pexels for stock media."""
    api_key = os.getenv("PEXELS_API_KEY", "")
    if not api_key:
        return []

    endpoint = f"https://api.pexels.com/v1/search" if media_type == "photos" else f"https://api.pexels.com/videos/search"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                endpoint,
                params={"query": query, "per_page": per_page, "orientation": "landscape"},
                headers={"Authorization": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            items = data.get("photos", []) or data.get("videos", [])
            for item in items:
                if media_type == "photos":
                    results.append({
                        "id": item["id"],
                        "url": item["src"]["large2x"],
                        "width": item["width"],
                        "height": item["height"],
                        "photographer": item.get("photographer", ""),
                    })
                else:
                    video_files = item.get("video_files", [])
                    hd = next((f for f in video_files if f.get("quality") == "hd"), video_files[0] if video_files else {})
                    results.append({
                        "id": item["id"],
                        "url": hd.get("link", ""),
                        "width": hd.get("width", 0),
                        "height": hd.get("height", 0),
                        "duration": item.get("duration", 0),
                    })
            return results

    except Exception as e:
        logger.warning("pexels.search_failed", error=str(e))
        return []


async def download_media(
    url: str,
    output_dir: Path,
    filename: str = "",
) -> Path | None:
    """Download a media file from URL."""
    output_dir.mkdir(parents=True, exist_ok=True)

    if not filename:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        filename = Path(parsed.path).name or "downloaded_media"

    output_path = output_dir / filename

    try:
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            output_path.write_bytes(resp.content)
            return output_path
    except Exception as e:
        logger.warning("download.failed", url=url, error=str(e))
        return None
