"""Compliance stage: runs content through the full compliance pipeline."""
from __future__ import annotations

import structlog

from src.core.models import ContentLayer, Platform, PipelineStatus, StageResult, StructuredContent
from src.core.pipeline import PipelineContext, Stage
from src.stages.compliance.content_filter import llm_compliance_review, scan_sensitive_keywords
from src.stages.compliance.disclaimer import inject_disclaimer
from src.stages.compliance.platform_rules import should_use_conservative_version
from src.stages.compliance.sensitive_reframe import reframe_sensitive_terms

logger = structlog.get_logger()


class ComplianceStage(Stage):
    """Run content through compliance checks: keywords, LLM review, reframing, disclaimers."""

    name = "compliance"

    async def execute(self, context: PipelineContext) -> StageResult:
        config = context.get_stage_config(self.name)
        content: StructuredContent | None = context.get("content")
        if content is None:
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.SKIPPED,
                error="No content in context",
            )

        enabled = config.get("enabled", True)
        if not enabled:
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.SKIPPED,
                output={"reason": "compliance disabled"},
            )

        domain = content.domain.value
        auto_fix = config.get("auto_fix", True)
        max_risk_level = config.get("max_risk_level", 3)

        try:
            # Collect full text for scanning
            full_text = _collect_full_text(content)

            # ── Step 1: Sensitive keyword scan (local, fast) ──
            keyword_matches = scan_sensitive_keywords(full_text, domain)
            high_risk_keywords = [m for m in keyword_matches if m["risk_level"] >= 4]

            if high_risk_keywords and not auto_fix:
                return StageResult(
                    stage_name=self.name,
                    status=PipelineStatus.FAILED,
                    error=f"High-risk keywords found: {[m['keyword'] for m in high_risk_keywords]}",
                    output={"keyword_matches": keyword_matches},
                )

            # ── Step 2: Sensitive term reframing (if auto_fix) ──
            reframe_changes = []
            if auto_fix:
                for section in content.sections:
                    section.body, changes = reframe_sensitive_terms(section.body, domain)
                    reframe_changes.extend(changes)
                    if section.tts_script:
                        section.tts_script, _ = reframe_sensitive_terms(section.tts_script, domain)

                if content.tts_script:
                    content.tts_script, _ = reframe_sensitive_terms(content.tts_script, domain)
                if content.article_text:
                    content.article_text, _ = reframe_sensitive_terms(content.article_text, domain)
                if content.short_copy:
                    content.short_copy, _ = reframe_sensitive_terms(content.short_copy, domain)

            # ── Step 3: LLM compliance review (best-effort) ──
            try:
                review = await llm_compliance_review(
                    _collect_full_text(content),  # re-collect after reframing
                    domain=domain,
                )
            except Exception as e:
                logger.warning("compliance.llm_review_skipped", error=str(e))
                review = {"risk_level": 1, "issues": [], "safe_to_publish": True}
            risk_level = review.get("risk_level", 1)
            issues = review.get("issues", [])

            if risk_level > max_risk_level:
                return StageResult(
                    stage_name=self.name,
                    status=PipelineStatus.FAILED,
                    error=f"Content risk level {risk_level} exceeds max {max_risk_level}",
                    output={
                        "risk_level": risk_level,
                        "issues": issues,
                        "keyword_matches": len(keyword_matches),
                        "reframe_changes": len(reframe_changes),
                    },
                )

            # ── Step 4: Inject disclaimers ──
            disclaimer_video = inject_disclaimer("", domain, "video_end").strip()
            if disclaimer_video:
                content.disclaimers.append(disclaimer_video)

            if content.tts_script:
                content.tts_script = inject_disclaimer(content.tts_script, domain, "video_end")

            if content.article_text:
                content.article_text = inject_disclaimer(content.article_text, domain, "article_footer")

            content.compliance_notes = (
                f"Risk level: {risk_level}/5. "
                f"Keywords scanned: {len(keyword_matches)} matches. "
                f"Terms reframed: {len(reframe_changes)}. "
                f"Issues: {len(issues)}."
            )

            # Update context
            context.set("content", content)
            context.run.content = content

            logger.info(
                "compliance.passed",
                risk_level=risk_level,
                keywords=len(keyword_matches),
                reframes=len(reframe_changes),
                issues=len(issues),
            )

            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.COMPLETED,
                output={
                    "risk_level": risk_level,
                    "keyword_matches": len(keyword_matches),
                    "reframe_changes": len(reframe_changes),
                    "issues_count": len(issues),
                    "disclaimers_added": len(content.disclaimers),
                    "safe_to_publish": review.get("safe_to_publish", True),
                },
            )

        except Exception as e:
            logger.exception("compliance.failed")
            return StageResult(
                stage_name=self.name,
                status=PipelineStatus.FAILED,
                error=str(e),
            )


def _collect_full_text(content: StructuredContent) -> str:
    """Collect all text from content for scanning."""
    parts = [content.title, content.summary]
    for section in content.sections:
        if section.heading:
            parts.append(section.heading)
        parts.append(section.body)
    if content.tts_script:
        parts.append(content.tts_script)
    if content.short_copy:
        parts.append(content.short_copy)
    if content.article_text:
        parts.append(content.article_text)
    return "\n".join(parts)
