"""LLM-driven storyboard generation from structured content."""
from __future__ import annotations

import json
from typing import Any

import structlog

from src.core.llm import get_llm
from src.core.models import ContentType, Scene, Storyboard, StructuredContent

logger = structlog.get_logger()

ENGINE_MAP = {
    ContentType.HOT_TAKE: "moviepy",
    ContentType.EMOTION_DECODE: "moviepy",
    ContentType.MYSTICAL_ALERT: "mystical",
    ContentType.DEEP_ANALYSIS: "remotion",
    ContentType.FRAMEWORK: "manim",
    ContentType.MYSTICAL_SYSTEM: "mystical",
}

STORYBOARD_PROMPT = """你是一位专业的视频分镜师。根据以下内容脚本，生成视频分镜脚本。

## 内容信息
标题: {title}
领域: {domain}
类型: {content_type}
总时长约: {duration}秒

## 内容段落
{sections}

## 分镜要求
为每个段落生成1-3个场景(scene)，总场景数控制在{max_scenes}个以内。

每个场景包含:
- scene_type: 场景类型 (chart/flowchart/image/text_animation/annotation/map/comparison/symbol_reveal/particle_effect/mandala/astro_chart/code_demo/data_reveal)
- description: 画面描述
- duration: 持续秒数 (基于对应文字长度估算)
- camera_move: 镜头运动 (static/push_in/pull_out/pan_left/pan_right/zoom_focus)
- transition: 转场效果 (fade/slide/wipe/zoom/dissolve)
- text_overlay: 需要叠加显示的文字 (标题/关键数据/要点)
- assets_needed: 需要的素材列表 (图片描述/图表类型/数据)

输出JSON:
{{
  "scenes": [
    {{
      "scene_type": "data_reveal",
      "description": "画面描述",
      "duration": 5.0,
      "camera_move": "push_in",
      "transition": "fade",
      "text_overlay": "关键文字",
      "assets_needed": ["柱状图: GDP增长数据"],
      "data": {{"chart_type": "bar", "title": "GDP增长率"}}
    }}
  ],
  "engine_hint": "推荐的渲染引擎 (remotion/moviepy/manim/mystical)"
}}"""


async def generate_storyboard(
    content: StructuredContent,
    max_scenes: int = 15,
    target_duration: float | None = None,
) -> Storyboard:
    """Generate a storyboard from structured content using LLM."""
    # Estimate duration from TTS script length
    if target_duration is None:
        char_count = len(content.tts_script or "")
        # Chinese speech: ~4 chars/second
        target_duration = max(30, char_count / 4)

    # Format sections for prompt
    sections_text = ""
    for i, sec in enumerate(content.sections):
        sections_text += f"\n### 段落 {i+1}"
        if sec.heading:
            sections_text += f" - {sec.heading}"
        sections_text += f"\n{sec.tts_script or sec.body}"
        if sec.visual_cue:
            sections_text += f"\n[视觉提示: {sec.visual_cue.description}]"

    prompt = STORYBOARD_PROMPT.format(
        title=content.title,
        domain=content.domain.value,
        content_type=content.content_type.value,
        duration=int(target_duration),
        sections=sections_text,
        max_scenes=max_scenes,
    )

    llm = get_llm()
    raw = await llm.generate_text(
        prompt=prompt,
        system="你是一位专业视频分镜师。输出纯JSON。",
        temperature=0.5,
    )

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("storyboard.parse_failed", raw=raw[:200])
        # Generate a simple fallback storyboard
        return _fallback_storyboard(content, target_duration)

    scenes = []
    for s in data.get("scenes", []):
        scenes.append(Scene(
            scene_type=s.get("scene_type", "text_animation"),
            description=s.get("description", ""),
            duration=float(s.get("duration", 5.0)),
            camera_move=s.get("camera_move", "static"),
            transition=s.get("transition", "fade"),
            text_overlay=s.get("text_overlay", ""),
            assets_needed=s.get("assets_needed", []),
            data=s.get("data", {}),
        ))

    engine_hint = data.get("engine_hint", "")
    if not engine_hint:
        engine_hint = ENGINE_MAP.get(content.content_type, "moviepy")

    return Storyboard(
        content_id=content.id,
        scenes=scenes,
        total_duration=sum(s.duration for s in scenes),
        engine_hint=engine_hint,
    )


def _fallback_storyboard(content: StructuredContent, duration: float) -> Storyboard:
    """Generate a simple fallback storyboard when LLM fails."""
    scenes = []
    n_sections = max(1, len(content.sections))
    per_section = duration / n_sections

    # Title scene
    scenes.append(Scene(
        scene_type="text_animation",
        description=f"标题展示: {content.title}",
        duration=3.0,
        transition="fade",
        text_overlay=content.title,
    ))

    for sec in content.sections:
        scenes.append(Scene(
            scene_type="image" if sec.visual_cue else "text_animation",
            description=sec.visual_cue.description if sec.visual_cue else sec.heading or "正文展示",
            duration=per_section,
            camera_move="push_in",
            transition="slide",
            text_overlay=sec.heading or "",
        ))

    return Storyboard(
        content_id=content.id,
        scenes=scenes,
        total_duration=sum(s.duration for s in scenes),
        engine_hint=ENGINE_MAP.get(content.content_type, "moviepy"),
    )
