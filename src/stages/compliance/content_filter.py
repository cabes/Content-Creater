"""Content compliance filter: sensitive keyword scanning + LLM review."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import structlog
import yaml

from src.core.config import CONFIG_DIR
from src.core.llm import get_llm
from src.core.models import Platform

logger = structlog.get_logger()


def load_sensitive_keywords() -> dict[str, list[str]]:
    """Load sensitive keywords organized by category."""
    path = CONFIG_DIR / "compliance" / "sensitive_keywords.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def scan_sensitive_keywords(
    text: str,
    domain: str = "general",
    platform: str = "general",
) -> list[dict[str, Any]]:
    """Scan text for sensitive keywords. Returns list of matches."""
    keywords_db = load_sensitive_keywords()
    matches = []

    # Check domain-specific keywords
    for category in [domain, "general", platform]:
        category_words = keywords_db.get(category, [])
        for entry in category_words:
            if isinstance(entry, str):
                word, level = entry, 3
            elif isinstance(entry, dict):
                word = entry.get("word", "")
                level = entry.get("level", 3)
            else:
                continue

            if word and word in text:
                matches.append({
                    "keyword": word,
                    "category": category,
                    "risk_level": level,
                    "positions": [m.start() for m in re.finditer(re.escape(word), text)],
                })

    return matches


async def llm_compliance_review(
    text: str,
    domain: str,
    platform: str = "general",
) -> dict[str, Any]:
    """Use LLM to perform compliance review from platform reviewer's perspective."""
    system = """你是一位内容平台审核员。从合规角度审查以下内容。

评估维度:
1. 是否含有虚假/误导信息
2. 是否含有敏感政治言论
3. 是否含有违规金融建议(未持牌)
4. 是否含有封建迷信内容(未学术化包装)
5. 是否含有歧视/仇恨言论

输出JSON:
{
  "risk_level": 1-5,
  "issues": [{"type": "类型", "detail": "具体问题", "suggestion": "修改建议"}],
  "safe_to_publish": true/false,
  "platform_specific_notes": "针对该平台的特别注意事项"
}"""

    llm = get_llm()
    raw = await llm.generate_text(
        prompt=f"审核领域: {domain}\n目标平台: {platform}\n\n内容:\n{text}",
        system=system,
        temperature=0.1,
    )

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.error("compliance.llm_review_parse_failed")
        return {"risk_level": 3, "issues": [], "safe_to_publish": True}
