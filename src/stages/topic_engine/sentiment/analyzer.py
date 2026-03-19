"""Sentiment analysis: lightweight NLP screening + LLM deep analysis."""
from __future__ import annotations

import json
from typing import Any

import structlog

from src.core.llm import get_llm
from src.core.models import SentimentSignal

logger = structlog.get_logger()


def quick_sentiment_screen(texts: list[str]) -> list[dict[str, Any]]:
    """Quick sentiment screening using snownlp (Chinese NLP).

    Filters out neutral content, keeps strong emotional signals.
    """
    try:
        from snownlp import SnowNLP
    except ImportError:
        logger.warning("snownlp not installed, skipping quick screen")
        return [{"text": t, "sentiment": 0.5, "is_strong": True} for t in texts]

    results = []
    for text in texts:
        if not text.strip():
            continue
        try:
            s = SnowNLP(text)
            score = s.sentiments  # 0-1, 0=negative, 1=positive
            # Strong emotion: far from neutral (0.5)
            is_strong = abs(score - 0.5) > 0.25
            results.append({
                "text": text,
                "sentiment": score,
                "is_strong": is_strong,
            })
        except Exception:
            results.append({"text": text, "sentiment": 0.5, "is_strong": False})

    return results


async def deep_sentiment_analysis(
    topics: list[dict[str, Any]],
    domain: str = "general",
) -> list[SentimentSignal]:
    """Use LLM for deep sentiment analysis on trending topics.

    Analyzes emotion distribution, identifies emotion gaps,
    and suggests content angles.
    """
    if not topics:
        return []

    # Format topics for LLM analysis
    topics_text = "\n".join(
        f"- [{t.get('platform', '?')}] (热度: {t.get('hot_score', 0)}) {t.get('title', '')}"
        + (f"\n  描述: {t['desc']}" if t.get("desc") else "")
        for t in topics[:15]
    )

    system_prompt = """你是一位社交媒体情绪分析专家。分析以下热门话题的公众情绪状态。

对每个值得做内容的话题，输出 JSON 数组，每个元素包含：
{
  "topic": "话题标题",
  "source": "平台",
  "emotion_distribution": {"anger": 0.0-1.0, "fear": 0.0-1.0, "excitement": 0.0-1.0, "confusion": 0.0-1.0, "sadness": 0.0-1.0},
  "intensity": 0-10,
  "trend": "rising/fading/polarizing/stable",
  "emotion_gap": "当前舆论缺少什么视角",
  "hook_angle": "Hook内容切入角度(短平快，情绪共振)",
  "value_angle": "Value内容衍生方向(深度、框架、体系)"
}

只选择情绪强度 ≥ 6 的话题。输出纯 JSON 数组，不要其他内容。"""

    llm = get_llm()
    try:
        raw = await llm.generate_text(
            prompt=f"当前领域: {domain}\n\n热门话题列表:\n{topics_text}",
            system=system_prompt,
            temperature=0.3,
        )
        # Parse JSON from response
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        signals_data = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("sentiment.llm_analysis_failed", error=str(e))
        return []

    signals = []
    for item in signals_data:
        try:
            signals.append(SentimentSignal(
                source=item.get("source", "unknown"),
                topic=item.get("topic", ""),
                emotion_distribution=item.get("emotion_distribution", {}),
                intensity=float(item.get("intensity", 0)),
                trend=item.get("trend", ""),
                emotion_gap=item.get("emotion_gap", ""),
                hook_angle=item.get("hook_angle", ""),
                value_angle=item.get("value_angle", ""),
            ))
        except Exception:
            logger.warning("sentiment.parse_signal_failed", item=item)
    return signals
