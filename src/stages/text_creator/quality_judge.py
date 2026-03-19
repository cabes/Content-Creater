"""LLM-as-Judge quality assessment for generated content."""
from __future__ import annotations

import json

import structlog

from src.core.llm import get_llm
from src.core.models import StructuredContent

logger = structlog.get_logger()

QUALITY_DIMENSIONS = [
    "factual_accuracy",   # 事实准确性
    "logical_rigor",      # 逻辑严谨性
    "domain_depth",       # 领域深度
    "originality",        # 原创观点
    "actionability",      # 可操作性
]

JUDGE_PROMPT = """你是一位严格的内容质量评审员。评估以下{domain}领域的{layer}内容。

## 内容
标题: {title}
正文:
{body}

## 评审维度 (每项0-10分)
1. **事实准确性** (factual_accuracy): 数据/引用是否可验证？有无明显错误？
2. **逻辑严谨性** (logical_rigor): 论证链是否完整？有无逻辑跳跃？
3. **领域深度** (domain_depth): 是否有专业洞见？还是只是常识复述？
4. **原创观点** (originality): 是否有独到视角？还是众所周知的结论？
5. **可操作性** (actionability): 读者看完能做什么？有无具体建议？

## 输出JSON
{{
  "scores": {{
    "factual_accuracy": 8,
    "logical_rigor": 7,
    "domain_depth": 6,
    "originality": 5,
    "actionability": 7
  }},
  "overall_score": 6.6,
  "weaknesses": ["问题1", "问题2"],
  "improvement_suggestions": ["建议1", "建议2"],
  "rewrite_needed": false,
  "rewrite_sections": []
}}"""


async def judge_content_quality(
    content: StructuredContent,
    min_score: float = 7.0,
) -> dict:
    """Assess content quality using LLM-as-Judge.

    Returns quality assessment with scores and improvement suggestions.
    """
    body = "\n\n".join(
        (f"## {s.heading}\n" if s.heading else "") + s.body
        for s in content.sections
    )

    prompt = JUDGE_PROMPT.format(
        domain=content.domain.value,
        layer=content.content_layer.value,
        title=content.title,
        body=body,
    )

    llm = get_llm()
    raw = await llm.generate_text(
        prompt=prompt,
        system="你是一位严格的内容质量评审员。输出纯JSON。",
        temperature=0.2,
    )

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("quality_judge.parse_failed")
        return {"overall_score": 0, "error": "Failed to parse judge response"}

    overall = result.get("overall_score", 0)
    result["passed"] = overall >= min_score
    return result
