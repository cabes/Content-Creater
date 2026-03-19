"""Hook content writer: short, punchy, emotion-driven content for traffic."""
from __future__ import annotations

import json

import structlog

from src.core.config import get_prompt_template
from src.core.llm import get_llm
from src.core.models import (
    ContentSection,
    EmotionMarker,
    EmotionType,
    StructuredContent,
    Topic,
    VisualCue,
)

logger = structlog.get_logger()

# Default hook writing prompt when template file doesn't exist
DEFAULT_HOOK_PROMPT = """你是一位顶尖短视频内容创作者，专注{domain}领域。

## 任务
为以下选题创作一条 Hook 短视频文案（1-3分钟口播脚本）。

## 选题信息
- 标题: {title}
- 角度: {angle}
- 关键词: {keywords}
- 情绪策略: {emotion_strategy}
- 调性: {tone}

## 写作要求
1. **开头5秒必须抓住注意力**：直击情绪痛点或抛出反直觉事实
2. **短段落、快节奏**：每段不超过3句话
3. **情绪标注**：在关键句子前用 [emotion:类型] 标记情绪
   可用情绪: excited, serious, tense, analytical, mystical, humorous, warm, urgent
4. **视觉提示**：每段附带 [visual:描述] 说明应展示什么画面
5. **数据/案例**：至少引用1个具体数据或案例
6. **口语化**：像聊天一样说话，不要书面语
7. **结尾CTA**: 引导观众关注或查看深度内容

## 输出JSON格式
{{
  "title": "视频标题(15字内，含数字或情绪词)",
  "summary": "一句话摘要",
  "sections": [
    {{
      "heading": "",
      "body": "段落正文(含情绪标注[emotion:xxx]...文本...[/emotion])",
      "visual_cue": "这段应展示什么画面",
      "tts_script": "纯口播版本(去掉标注，适合TTS朗读)"
    }}
  ],
  "tags": ["标签1", "标签2", "标签3"],
  "short_copy": "小红书/抖音短文案版本(100字内，含emoji和hashtag)",
  "cta_hooks": ["CTA话术1", "CTA话术2"]
}}"""


async def generate_hook_content(
    topic: Topic,
    max_length: int = 800,
    auto_link_value: bool = True,
) -> StructuredContent:
    """Generate hook (short-form, traffic-focused) content."""
    # Try to load domain-specific prompt template
    try:
        template_str = get_prompt_template(f"{topic.domain.value}_hook")
    except FileNotFoundError:
        template_str = DEFAULT_HOOK_PROMPT

    prompt = template_str.format(
        domain=topic.domain.value,
        title=topic.title,
        angle=topic.angle,
        keywords=", ".join(topic.keywords),
        emotion_strategy=topic.emotion_strategy,
        tone=topic.tone,
    )

    llm = get_llm()
    raw = await llm.generate_text(
        prompt=prompt,
        system="你是一位专业的短视频内容创作者。输出纯JSON。",
        temperature=0.7,
        max_tokens=2000,
    )

    # Parse JSON response
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("hook_writer.json_parse_failed", raw=raw[:200])
        raise

    # Build StructuredContent
    sections = []
    full_tts = []
    for sec in data.get("sections", []):
        visual_cue = None
        if sec.get("visual_cue"):
            visual_cue = VisualCue(description=sec["visual_cue"])

        sections.append(ContentSection(
            heading=sec.get("heading", ""),
            body=sec.get("body", ""),
            visual_cue=visual_cue,
            tts_script=sec.get("tts_script", ""),
        ))
        if sec.get("tts_script"):
            full_tts.append(sec["tts_script"])

    # Build CTA hooks
    cta_hooks = data.get("cta_hooks", [])
    if auto_link_value and topic.funnel_cta:
        cta_hooks.append(topic.funnel_cta)

    return StructuredContent(
        topic_id=topic.id,
        title=data.get("title", topic.title),
        summary=data.get("summary", ""),
        sections=sections,
        tags=data.get("tags", topic.keywords),
        tts_script="\n\n".join(full_tts),
        short_copy=data.get("short_copy", ""),
        cta_hooks=cta_hooks,
        domain=topic.domain,
        content_layer=topic.content_layer,
        content_type=topic.content_type,
        account_id=topic.account_id,
    )
