"""Reframe sensitive terminology into academic/acceptable language."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from src.core.config import CONFIG_DIR

# Default reframing rules when config file doesn't exist
DEFAULT_REFRAME_RULES = {
    "mystical": {
        "占星预测": "基于古典占星学的心理原型分析",
        "塔罗占卜": "塔罗牌的荣格心理学象征解读",
        "风水布局": "传统空间美学与环境心理学",
        "灵魂转世": "意识研究的前沿探讨",
        "通灵": "深层意识探索",
        "开光": "传统文化仪式的心理学意义",
        "改命": "认知重构与行为模式调整",
        "前世": "深层潜意识的原型叙事",
        "法术": "传统文化中的心理暗示技术",
        "诅咒": "负面心理暗示效应",
        "包治百病": "[移除，不使用绝对化表述]",
        "保证灵验": "[移除，不使用绝对化表述]",
    },
    "finance": {
        "保证收益": "[移除，不使用绝对化表述]",
        "稳赚不赔": "[移除，不使用绝对化表述]",
        "内幕消息": "市场信息分析",
        "割韭菜": "市场博弈",
        "庄家": "主力资金",
    },
}


def load_reframe_rules() -> dict[str, dict[str, str]]:
    """Load reframing rules from config."""
    path = CONFIG_DIR / "compliance" / "mystical_reframe.yaml"
    if path.exists():
        with open(path) as f:
            custom = yaml.safe_load(f) or {}
        merged = {**DEFAULT_REFRAME_RULES}
        for domain, rules in custom.items():
            merged.setdefault(domain, {}).update(rules)
        return merged
    return DEFAULT_REFRAME_RULES


def reframe_sensitive_terms(
    text: str,
    domain: str,
) -> tuple[str, list[dict[str, str]]]:
    """Replace sensitive terms with academic/acceptable alternatives.

    Returns (reframed_text, list of changes made).
    """
    rules = load_reframe_rules()
    domain_rules = rules.get(domain, {})
    changes = []

    for original, replacement in domain_rules.items():
        if original in text:
            if replacement.startswith("[移除"):
                # Remove the containing sentence
                text = text.replace(original, "")
                changes.append({"original": original, "action": "removed"})
            else:
                text = text.replace(original, replacement)
                changes.append({"original": original, "replacement": replacement})

    return text, changes
