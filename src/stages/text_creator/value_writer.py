"""Value content writer: deep, systematic, trust-building content."""
from __future__ import annotations

import json

import structlog

from src.core.config import get_prompt_template
from src.core.llm import get_llm
from src.core.models import (
    ContentSection,
    StructuredContent,
    Topic,
    VisualCue,
)

logger = structlog.get_logger()

DEFAULT_VALUE_PROMPT = """你是一位{persona}。

## 任务
为以下选题创作一篇深度内容（8-15分钟视频脚本 + 长文版本）。

## 选题信息
- 标题: {title}
- 角度: {angle}
- 关键词: {keywords}
- 调性: {tone}

## 写作要求
1. **金字塔结构**：先给结论，再展开论证
2. **深度论证**：数据+案例+理论+实操，四层递进
3. **认知升级感**：读完/看完有"原来如此"的顿悟
4. **至少引用3个具体数据源或案例**
5. **每个大段落附带视觉提示和情绪标注**
6. **自然植入1-2个商业转化锚点**（非硬广）
7. **结尾有可执行的行动建议**

## 输出JSON格式
{{
  "title": "标题(20字内)",
  "summary": "3句话摘要",
  "sections": [
    {{
      "heading": "章节标题",
      "body": "正文(含[emotion:xxx]...[/emotion]情绪标注)",
      "visual_cue": "视觉提示",
      "tts_script": "口播版本"
    }}
  ],
  "tags": ["标签1", "标签2"],
  "article_text": "公众号长文版本(Markdown格式)",
  "monetization_anchor": "自然的商业转化话术",
  "cta_hooks": ["深度CTA"]
}}"""

# Expert personas by domain
PERSONAS = {
    "finance": "有15年投行经验的宏观策略分析师",
    "geopolitics": "国际关系学者，专注大国博弈研究20年",
    "mystical": "融合古典占星与荣格心理学的灵性导师，研修20年",
    "knowledge": "跨学科研究者，擅长第一性原理思维和类比解释",
}


async def generate_value_content(
    topic: Topic,
    min_length: int = 3000,
    enable_framework: bool = True,
    monetization_anchor: bool = True,
) -> StructuredContent:
    """Generate value (long-form, depth-focused) content."""
    persona = PERSONAS.get(topic.domain.value, "资深内容创作者")

    try:
        template_str = get_prompt_template(f"{topic.domain.value}_value")
    except FileNotFoundError:
        template_str = DEFAULT_VALUE_PROMPT

    prompt = template_str.format(
        persona=persona,
        title=topic.title,
        angle=topic.angle,
        keywords=", ".join(topic.keywords),
        tone=topic.tone,
    )

    llm = get_llm()
    raw = await llm.generate_text(
        prompt=prompt,
        system=f"你是一位{persona}。输出纯JSON。",
        temperature=0.6,
        max_tokens=4096,
    )

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("value_writer.json_parse_failed", raw=raw[:200])
        raise

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

    return StructuredContent(
        topic_id=topic.id,
        title=data.get("title", topic.title),
        summary=data.get("summary", ""),
        sections=sections,
        tags=data.get("tags", topic.keywords),
        tts_script="\n\n".join(full_tts),
        article_text=data.get("article_text", ""),
        cta_hooks=data.get("cta_hooks", []),
        monetization_anchor=data.get("monetization_anchor", ""),
        domain=topic.domain,
        content_layer=topic.content_layer,
        content_type=topic.content_type,
        account_id=topic.account_id,
    )
