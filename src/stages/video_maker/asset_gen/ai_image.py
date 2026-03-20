"""AI image generation via SiliconFlow Kolors / Replicate API."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import structlog

from src.core.config import get_settings

logger = structlog.get_logger()

# Domain-specific style prompts
STYLE_PROMPTS = {
    "finance": "professional, corporate, modern, clean composition, blue tones, cinematic lighting, 4k photography",
    "geopolitics": "photojournalistic, dramatic lighting, dark atmosphere, documentary style, wide angle, 4k",
    "mystical": "mystical atmosphere, cosmic, dark purple and gold, ethereal glow, sacred geometry, starfield, 4k",
    "knowledge": "educational, modern, bright, clean design, technology feel, 4k photography",
}

# Scene keyword to image prompt mapping
SCENE_PROMPTS = {
    "production": "modern factory production line with robotic arms, industrial machinery, manufacturing floor, cinematic warm lighting",
    "logistics": "logistics warehouse with automated conveyor belts, packages being sorted, modern distribution center, wide angle",
    "port": "busy container port with cargo ships and cranes loading containers, aerial view, blue hour, cinematic",
    "consumer": "busy shopping district, modern retail stores with window displays, consumers with shopping bags, vibrant",
    "data_flow": "digital data streams, holographic displays showing charts, futuristic control room, blue neon lighting",
    "stock_market": "stock exchange trading floor, multiple screens showing stock charts and tickers, dramatic side lighting",
    "city_skyline": "modern city skyline at dusk, financial district glass towers reflecting sunset, dramatic clouds",
    "global_trade": "world map with glowing shipping routes, container ships on ocean, satellite view, blue tones",
    "meeting": "corporate boardroom meeting, professionals in discussion, modern glass office, natural lighting",
    "technology": "modern data center server racks with blue LED lights, technology infrastructure, clean",
    "economy": "modern city with construction cranes and new buildings, economic growth, sunrise, optimistic wide angle",
    "crisis": "stormy dramatic sky over financial district, dark clouds gathering, tension, cinematic moody",
    "recovery": "golden sunrise over city skyline, warm light breaking through clouds, hope and optimism",
    "investment": "person analyzing financial data on multiple monitors, charts and graphs, modern office setup",
    "currency": "international currency symbols floating, global finance concept, dark background with golden elements",
    "energy": "renewable energy landscape, wind turbines and solar panels, green hills, bright sky",
    "real_estate": "modern residential buildings and city development, architectural photography, golden hour",
}


async def generate_ai_image(
    prompt: str,
    domain: str = "finance",
    width: int = 1920,
    height: int = 1080,
    output_dir: Path | None = None,
) -> Path | None:
    """Generate an AI image using SiliconFlow Kolors or Replicate."""
    if output_dir is None:
        settings = get_settings()
        output_dir = settings.media_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)

    style = STYLE_PROMPTS.get(domain, STYLE_PROMPTS["finance"])
    full_prompt = f"{prompt}, {style}"

    # Try SiliconFlow Kolors (reuse LLM API key)
    settings = get_settings()
    sf_key = settings.llm.api_key
    if sf_key and "siliconflow" in (settings.llm.base_url or ""):
        result = await _generate_siliconflow(full_prompt, sf_key, width, height, output_dir)
        if result:
            return result

    # Try Replicate
    replicate_token = os.getenv("REPLICATE_API_TOKEN", "")
    if replicate_token:
        return await _generate_replicate(full_prompt, replicate_token, width, height, output_dir)

    logger.warning("ai_image.no_provider")
    return None


async def generate_scene_image(
    scene_type: str,
    description: str = "",
    domain: str = "finance",
    output_dir: Path | None = None,
) -> Path | None:
    """Generate an image for a specific scene type."""
    prompt = _match_scene_prompt(scene_type, description, domain)
    return await generate_ai_image(prompt, domain=domain, output_dir=output_dir)


def _match_scene_prompt(scene_type: str, description: str, domain: str) -> str:
    """Match scene description to a curated image prompt."""
    desc_lower = (description + " " + scene_type).lower()

    keyword_map = {
        "生产": "production", "制造": "production", "工厂": "production",
        "物流": "logistics", "仓储": "logistics", "配送": "logistics",
        "港口": "port", "集装箱": "port", "海运": "port", "船": "port",
        "消费": "consumer", "购物": "consumer", "零售": "consumer",
        "数据": "data_flow", "信息": "data_flow", "digital": "data_flow",
        "股": "stock_market", "交易": "stock_market", "market": "stock_market",
        "城市": "city_skyline", "skyline": "city_skyline",
        "贸易": "global_trade", "全球化": "global_trade", "国际": "global_trade",
        "会议": "meeting", "讨论": "meeting",
        "服务器": "technology", "科技": "technology", "tech": "technology",
        "经济": "economy", "增长": "economy", "gdp": "economy",
        "复苏": "recovery", "回暖": "recovery", "反弹": "recovery",
        "危机": "crisis", "下跌": "crisis", "衰退": "crisis",
        "投资": "investment", "理财": "investment", "资产": "investment",
        "货币": "currency", "汇率": "currency", "美元": "currency",
        "能源": "energy", "新能源": "energy", "石油": "energy",
        "房": "real_estate", "楼市": "real_estate",
    }

    for keyword, scene_key in keyword_map.items():
        if keyword in desc_lower:
            return SCENE_PROMPTS.get(scene_key, description)

    domain_defaults = {
        "finance": "stock_market",
        "geopolitics": "city_skyline",
        "mystical": "data_flow",
        "knowledge": "technology",
    }
    return SCENE_PROMPTS.get(domain_defaults.get(domain, "city_skyline"), description)


async def _generate_siliconflow(
    prompt: str, api_key: str, width: int, height: int, output_dir: Path,
) -> Path | None:
    try:
        size_str = f"{width}x{height}"
        supported = ["1024x1024", "960x1280", "1280x960", "1920x1080", "1080x1920"]
        if size_str not in supported:
            size_str = "1280x960"

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.siliconflow.cn/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "Kwai-Kolors/Kolors",
                    "prompt": prompt,
                    "image_size": size_str,
                    "num_inference_steps": 20,
                },
            )
            if resp.status_code != 200:
                logger.warning("siliconflow_image.failed", status=resp.status_code, body=resp.text[:200])
                return None

            data = resp.json()
            images = data.get("images", data.get("data", []))
            if not images:
                return None
            url = images[0].get("url", "")
            if not url:
                return None

            img_resp = await client.get(url)
            img_path = output_dir / f"ai_{uuid4().hex[:8]}.png"
            img_path.write_bytes(img_resp.content)
            logger.info("ai_image.generated", path=str(img_path))
            return img_path

    except Exception as e:
        logger.warning("siliconflow_image.error", error=str(e))
        return None


async def _generate_replicate(
    prompt: str, api_token: str, width: int, height: int, output_dir: Path,
) -> Path | None:
    import asyncio
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.replicate.com/v1/predictions",
                headers={"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"},
                json={"model": "black-forest-labs/flux-1.1-pro", "input": {"prompt": prompt, "width": width, "height": height}},
            )
            resp.raise_for_status()
            pid = resp.json()["id"]
            for _ in range(60):
                await asyncio.sleep(2)
                r = await client.get(f"https://api.replicate.com/v1/predictions/{pid}", headers={"Authorization": f"Bearer {api_token}"})
                d = r.json()
                if d["status"] == "succeeded":
                    url = d["output"][0] if isinstance(d["output"], list) else d["output"]
                    img = await client.get(url)
                    p = output_dir / f"ai_{uuid4().hex[:8]}.png"
                    p.write_bytes(img.content)
                    return p
                elif d["status"] == "failed":
                    return None
    except Exception as e:
        logger.warning("replicate.error", error=str(e))
    return None
