"""Auto-inject disclaimers based on domain and platform."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.core.config import CONFIG_DIR

# Default disclaimers when config file doesn't exist
DEFAULT_DISCLAIMERS = {
    "finance": {
        "video_end": "本内容仅供学习交流，不构成任何投资建议。投资有风险，入市需谨慎。",
        "article_footer": "**免责声明**：本文内容仅代表个人观点，不构成投资建议。任何投资决策请基于您自身的独立判断。过往业绩不代表未来表现。",
        "short_disclaimer": "仅供学习，非投资建议",
    },
    "geopolitics": {
        "video_end": "本内容基于公开信息分析，仅供参考，不代表任何政治立场。",
        "article_footer": "**声明**：本文分析基于公开信息来源，旨在提供多元视角，不代表任何政治立场或倾向。",
        "short_disclaimer": "基于公开信息，仅供参考",
    },
    "mystical": {
        "video_end": "本内容基于古典占星学/传统文化的学术探讨，仅供文化研究和个人反思参考，不具有预测未来的功能。",
        "article_footer": "**学术声明**：本文内容基于占星学、心理学和传统文化的跨学科研究视角，旨在探讨人类认知和文化传统。所有解读仅供个人反思和学术讨论，不构成任何形式的预测或建议。",
        "short_disclaimer": "文化研究视角，仅供参考",
    },
    "knowledge": {
        "video_end": "本内容仅代表个人见解，欢迎批评指正。",
        "article_footer": "**声明**：本文观点仅代表作者个人见解，欢迎讨论和批评指正。",
        "short_disclaimer": "个人见解，欢迎讨论",
    },
}


def load_disclaimers() -> dict[str, Any]:
    """Load disclaimer templates from config."""
    path = CONFIG_DIR / "compliance" / "disclaimers.yaml"
    if not path.exists():
        return DEFAULT_DISCLAIMERS
    with open(path) as f:
        return yaml.safe_load(f) or DEFAULT_DISCLAIMERS


def get_disclaimer(
    domain: str,
    format_type: str = "video_end",
) -> str:
    """Get appropriate disclaimer for domain and format."""
    disclaimers = load_disclaimers()
    domain_disclaimers = disclaimers.get(domain, disclaimers.get("knowledge", {}))
    return domain_disclaimers.get(format_type, "")


def inject_disclaimer(
    text: str,
    domain: str,
    format_type: str = "video_end",
) -> str:
    """Inject disclaimer at the end of content."""
    disclaimer = get_disclaimer(domain, format_type)
    if disclaimer and disclaimer not in text:
        text = text.rstrip() + "\n\n" + disclaimer
    return text
