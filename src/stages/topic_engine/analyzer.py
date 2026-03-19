"""LLM-powered topic analysis, scoring, and selection."""
from __future__ import annotations

import json
from typing import Any

import structlog

from src.core.llm import get_llm
from src.core.models import (
    ContentDomain,
    ContentLayer,
    ContentType,
    Platform,
    SentimentSignal,
    Topic,
)
from src.stages.topic_engine.sentiment.strategy import (
    determine_content_type,
    determine_strategy,
    score_hook_topic,
)

logger = structlog.get_logger()

# Platform targeting by domain and layer
PLATFORM_TARGETS = {
    ("finance", "hook"): [Platform.DOUYIN, Platform.XIAOHONGSHU, Platform.BILIBILI],
    ("finance", "value"): [Platform.BILIBILI, Platform.WECHAT, Platform.PODCAST],
    ("geopolitics", "hook"): [Platform.BILIBILI, Platform.WEIBO],
    ("geopolitics", "value"): [Platform.BILIBILI, Platform.WECHAT, Platform.YOUTUBE],
    ("mystical", "hook"): [Platform.XIAOHONGSHU, Platform.DOUYIN],
    ("mystical", "value"): [Platform.XIAOHONGSHU, Platform.WECHAT, Platform.PODCAST, Platform.BILIBILI],
    ("knowledge", "hook"): [Platform.DOUYIN, Platform.BILIBILI],
    ("knowledge", "value"): [Platform.BILIBILI, Platform.WECHAT],
}

ACCOUNT_MAPPING = {
    "finance": "finance_account",
    "geopolitics": "geopolitics_account",
    "mystical": "mystical_account",
    "knowledge": "knowledge_account",
}


async def analyze_and_select_topics(
    trending: list[dict[str, Any]],
    sentiment_signals: list[SentimentSignal],
    domain: ContentDomain,
    layer: ContentLayer = ContentLayer.HOOK,
    max_topics: int = 5,
    calendar_events: list[dict[str, Any]] | None = None,
) -> list[Topic]:
    """Analyze trending data + sentiment signals and produce ranked topics."""

    # Build context for LLM
    trending_text = "\n".join(
        f"- [{t.get('platform')}] {t.get('title')} (热度:{t.get('hot_score', 0)})"
        for t in trending[:20]
    )

    signals_text = "\n".join(
        f"- {s.topic}: 情绪强度={s.intensity}, 缺口={s.emotion_gap}, Hook角度={s.hook_angle}"
        for s in sentiment_signals
    )

    calendar_text = ""
    if calendar_events:
        calendar_text = "\n日历事件:\n" + "\n".join(
            f"- {e.get('date')}: {e.get('topic_hint', '')}"
            for e in calendar_events
        )

    layer_instruction = ""
    if layer == ContentLayer.HOOK:
        layer_instruction = """
你正在为【情绪流量层 Hook Content】选题。要求:
- 追逐社会情绪，制造共鸣，获取流量
- 短平快、强标题、情绪共振
- 为每个选题建议一个关联的 Value 深度选题方向
- 时效性优先"""
    else:
        layer_instruction = """
你正在为【认知价值层 Value Content】选题。要求:
- 提供底层认知框架和解决方案
- 深度、体系化、高信息密度
- 建议关联的商业转化方向
- 常青内容设计，注重长尾流量"""

    system_prompt = f"""你是一位资深内容策划专家，专注{domain.value}领域。
{layer_instruction}

基于以下热点数据和情绪分析，选出最值得做的{max_topics}个选题。

对每个选题输出JSON数组:
[{{
  "title": "视频标题(吸引眼球)",
  "keywords": ["关键词1", "关键词2"],
  "angle": "具体切入角度",
  "tone": "内容调性",
  "linked_value_direction": "关联的Value内容方向(仅Hook需要)",
  "funnel_cta": "导流话术",
  "source_topic": "来源热点话题"
}}]

输出纯JSON，不要其他内容。"""

    prompt = f"热门话题:\n{trending_text}\n\n情绪分析:\n{signals_text}{calendar_text}"

    llm = get_llm()
    try:
        raw = await llm.generate_text(prompt=prompt, system=system_prompt, temperature=0.5)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        topics_data = json.loads(raw)
    except Exception as e:
        logger.error("topic_analyzer.llm_failed", error=str(e))
        return []

    # Build Topic objects
    topics: list[Topic] = []
    platform_key = (domain.value, layer.value)
    target_platforms = PLATFORM_TARGETS.get(platform_key, [Platform.BILIBILI])
    account_id = ACCOUNT_MAPPING.get(domain.value, "default")

    for item in topics_data[:max_topics]:
        # Match with sentiment signal if available
        matched_signal = None
        for s in sentiment_signals:
            if s.topic and s.topic in item.get("source_topic", ""):
                matched_signal = s
                break

        strategy = {}
        if matched_signal:
            strategy = determine_strategy(matched_signal, domain)

        dominant_emotion = strategy.get("dominant_emotion", "")
        content_type = determine_content_type(layer, domain, dominant_emotion)
        hook_score = 0.0
        if matched_signal:
            hot = next(
                (t.get("hot_score", 0) for t in trending if matched_signal.topic in t.get("title", "")),
                0,
            )
            hook_score = score_hook_topic(matched_signal, hot)

        topics.append(Topic(
            title=item.get("title", ""),
            keywords=item.get("keywords", []),
            angle=item.get("angle", ""),
            domain=domain,
            content_layer=layer,
            content_type=content_type,
            target_platforms=target_platforms,
            account_id=account_id,
            hook_score=hook_score,
            funnel_cta=item.get("funnel_cta", ""),
            sentiment_signals=[matched_signal] if matched_signal else [],
            emotion_strategy=strategy.get("hook_strategy", ""),
            tone=item.get("tone", strategy.get("tone", "")),
            source=item.get("source_topic", ""),
        ))

    # Sort by score
    topics.sort(key=lambda t: t.hook_score, reverse=True)
    return topics
