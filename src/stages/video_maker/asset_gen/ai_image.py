"""AI image generation via Replicate API (Flux Pro / SD3.5)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import structlog

from src.core.config import get_settings

logger = structlog.get_logger()

# Domain-specific style prompts for consistent aesthetics
STYLE_PROMPTS = {
    "finance": "professional, corporate, data visualization, clean modern design, blue and white color scheme, high quality",
    "geopolitics": "photojournalistic, documentary style, world map, dark gray and red color scheme, dramatic lighting",
    "mystical": "mystical atmosphere, cosmic, dark purple and gold, ethereal glow, sacred geometry, starfield, occult symbolism, high detail",
    "knowledge": "educational, infographic style, clean design, bright colors, modern illustration",
}


async def generate_ai_image(
    prompt: str,
    domain: str = "knowledge",
    width: int = 1920,
    height: int = 1080,
    output_dir: Path | None = None,
    model: str = "black-forest-labs/flux-1.1-pro",
) -> Path | None:
    """Generate an AI image using Replicate API."""
    import os
    api_token = os.getenv("REPLICATE_API_TOKEN", "")
    if not api_token:
        logger.warning("ai_image.no_replicate_token")
        return None

    if output_dir is None:
        settings = get_settings()
        output_dir = settings.media_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Add domain style
    style = STYLE_PROMPTS.get(domain, STYLE_PROMPTS["knowledge"])
    full_prompt = f"{prompt}, {style}"

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # Create prediction
            resp = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "input": {
                        "prompt": full_prompt,
                        "width": width,
                        "height": height,
                        "num_outputs": 1,
                    },
                },
            )
            resp.raise_for_status()
            prediction = resp.json()
            prediction_id = prediction["id"]

            # Poll for completion
            for _ in range(60):
                import asyncio
                await asyncio.sleep(2)

                resp = await client.get(
                    f"https://api.replicate.com/v1/predictions/{prediction_id}",
                    headers={"Authorization": f"Bearer {api_token}"},
                )
                data = resp.json()

                if data["status"] == "succeeded":
                    output_url = data["output"]
                    if isinstance(output_url, list):
                        output_url = output_url[0]

                    # Download image
                    img_resp = await client.get(output_url)
                    img_path = output_dir / f"{prediction_id}.png"
                    img_path.write_bytes(img_resp.content)
                    logger.info("ai_image.generated", path=str(img_path))
                    return img_path

                elif data["status"] == "failed":
                    logger.error("ai_image.failed", error=data.get("error"))
                    return None

        logger.warning("ai_image.timeout")
        return None

    except Exception as e:
        logger.exception("ai_image.error")
        return None
