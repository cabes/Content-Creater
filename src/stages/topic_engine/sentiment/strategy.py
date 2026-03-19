"""Map sentiment signals to topic selection strategies."""
from __future__ import annotations

from src.core.models import ContentDomain, ContentLayer, ContentType, EmotionType, SentimentSignal


# Emotion-driven decision matrix
EMOTION_STRATEGY_MATRIX = {
    "anger": {
        "hook_strategy": "理性拆解: '为什么会这样'",
        "value_direction": "结构性问题的底层分析",
        "tone": "冷静权威",
        "emotion_type": EmotionType.SERIOUS,
    },
    "fear": {
        "hook_strategy": "应对指南: '你该怎么办'",
        "value_direction": "风险管理/资产配置框架",
        "tone": "温暖专业",
        "emotion_type": EmotionType.WARM,
    },
    "confusion": {
        "hook_strategy": "科普梳理: '一次讲清楚'",
        "value_direction": "认知框架建设",
        "tone": "清晰简洁",
        "emotion_type": EmotionType.ANALYTICAL,
    },
    "excitement": {
        "hook_strategy": "逆向思考: '冷静一下'",
        "value_direction": "历史规律/周期理论",
        "tone": "理性克制",
        "emotion_type": EmotionType.ANALYTICAL,
    },
    "sadness": {
        "hook_strategy": "共情+出路: '你不是一个人'",
        "value_direction": "心理韧性/成长框架",
        "tone": "温暖坚定",
        "emotion_type": EmotionType.WARM,
    },
}


def determine_strategy(signal: SentimentSignal, domain: ContentDomain) -> dict:
    """Determine content strategy based on dominant emotion and domain."""
    # Find dominant emotion
    emotions = signal.emotion_distribution
    if not emotions:
        return {"tone": "中性客观", "emotion_type": EmotionType.ANALYTICAL}

    dominant_emotion = max(emotions, key=emotions.get)
    strategy = EMOTION_STRATEGY_MATRIX.get(dominant_emotion, {})

    # Domain-specific adjustments
    if domain == ContentDomain.MYSTICAL:
        strategy = {
            **strategy,
            "hook_strategy": "天象/能量解读: '宇宙的信号'",
            "value_direction": "修行体系/实修方法论",
            "tone": "深邃神秘",
            "emotion_type": EmotionType.MYSTICAL,
        }

    return {
        "dominant_emotion": dominant_emotion,
        "hook_strategy": strategy.get("hook_strategy", ""),
        "value_direction": strategy.get("value_direction", ""),
        "tone": strategy.get("tone", "中性客观"),
        "emotion_type": strategy.get("emotion_type", EmotionType.ANALYTICAL),
    }


def score_hook_topic(signal: SentimentSignal, hot_score: float = 0) -> float:
    """Calculate hook topic score using weighted formula."""
    # Normalize hot_score to 0-10
    norm_hot = min(hot_score / 1_000_000, 10) if hot_score > 0 else 5

    # Timeliness (newer = higher, simplified)
    timeliness = 8.0  # Default for fresh topics

    # Emotion gap value (presence of gap = higher value)
    gap_value = 8.0 if signal.emotion_gap else 3.0

    score = (
        norm_hot * 0.3
        + signal.intensity * 0.3
        + gap_value * 0.25
        + timeliness * 0.15
    )
    return round(score, 2)


def determine_content_type(
    layer: ContentLayer,
    domain: ContentDomain,
    dominant_emotion: str = "",
) -> ContentType:
    """Determine content type from layer x domain x emotion."""
    if layer == ContentLayer.HOOK:
        if domain == ContentDomain.MYSTICAL:
            return ContentType.MYSTICAL_ALERT
        if dominant_emotion in ("confusion", "anger"):
            return ContentType.EMOTION_DECODE
        return ContentType.HOT_TAKE

    # Value layer
    if domain == ContentDomain.MYSTICAL:
        return ContentType.MYSTICAL_SYSTEM
    if dominant_emotion in ("confusion", "fear"):
        return ContentType.FRAMEWORK
    return ContentType.DEEP_ANALYSIS
