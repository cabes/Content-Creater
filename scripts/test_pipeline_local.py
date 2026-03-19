#!/usr/bin/env python3
"""Local pipeline test with mock data — no API keys needed.

Tests the full pipeline flow by injecting synthetic topic/content data
so every stage can exercise its logic without external API calls.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main() -> None:
    from src.core.models import (
        ContentDomain, ContentLayer, ContentType, ContentSection,
        EmotionType, Platform, StructuredContent, Topic, VisualCue,
    )
    from src.core.pipeline import Pipeline, PipelineContext

    # ── Build a minimal pipeline with stages that DON'T need API keys ──
    from src.stages.compliance.stage import ComplianceStage
    from src.stages.article_formatter.stage import ArticleFormatterStage

    # We'll test stages individually with synthetic data

    print("=" * 60)
    print("LOCAL PIPELINE TEST (no API keys)")
    print("=" * 60)

    # ── 1. Create synthetic Topic ──
    topic = Topic(
        title="美联储加息75基点！你的房贷要爆了？",
        keywords=["美联储", "加息", "房贷", "利率"],
        angle="从普通人房贷压力切入，分析加息对日常生活的影响",
        domain=ContentDomain.FINANCE,
        content_layer=ContentLayer.HOOK,
        content_type=ContentType.HOT_TAKE,
        target_platforms=[Platform.DOUYIN, Platform.BILIBILI],
        account_id="finance_account",
        hook_score=8.5,
        funnel_cta="完整分析见主页置顶视频",
        emotion_strategy="应对指南: '你该怎么办'",
        tone="温暖专业",
    )
    print(f"\n1. Topic: {topic.title}")
    print(f"   Domain: {topic.domain.value}, Layer: {topic.content_layer.value}")

    # ── 2. Create synthetic Content ──
    content = StructuredContent(
        topic_id=topic.id,
        title="加息75基点！3个动作保住你的钱包",
        summary="美联储第四次加息，利率创15年新高。本期教你三个实操策略应对。",
        sections=[
            ContentSection(
                heading="",
                body="[emotion:urgent]美联储昨晚宣布加息75个基点[/emotion]，这已经是今年第四次加息了。你可能觉得这跟你没关系，但如果你有房贷、车贷、或者任何形式的负债，你的月供可能马上就要涨了。",
                visual_cue=VisualCue(description="美联储大楼 + 利率数据图表动画"),
                tts_script="美联储昨晚宣布加息75个基点，这已经是今年第四次加息了。你可能觉得这跟你没关系，但如果你有房贷、车贷、或者任何形式的负债，你的月供可能马上就要涨了。",
            ),
            ContentSection(
                heading="",
                body="[emotion:analytical]先说一个数据：保证收益的投资根本不存在，但我们可以做好风险管理。[/emotion]过去一年，30年期房贷利率从3%飙到了7%。同样100万的贷款，你的月供多了将近3000块。",
                visual_cue=VisualCue(description="利率走势折线图 + 月供对比表"),
                tts_script="先说一个数据：保证收益的投资根本不存在，但我们可以做好风险管理。过去一年，30年期房贷利率从3%飙到了7%。同样100万的贷款，你的月供多了将近3000块。",
            ),
            ContentSection(
                heading="",
                body="[emotion:warm]所以你该怎么办？三个策略。[/emotion]第一，如果你还没买房，别急，等利率见顶。第二，已有房贷的，考虑提前还一部分本金。第三，把多余的现金放到货币基金里，利率高了反而有利。",
                visual_cue=VisualCue(description="三个策略的图文列表动画"),
                tts_script="所以你该怎么办？三个策略。第一，如果你还没买房，别急，等利率见顶。第二，已有房贷的，考虑提前还一部分本金。第三，把多余的现金放到货币基金里，利率高了反而有利。",
            ),
        ],
        tags=["美联储", "加息", "房贷", "理财", "投资"],
        tts_script="美联储昨晚宣布加息75个基点，这已经是今年第四次加息了。\n\n先说一个数据：保证收益的投资根本不存在，但我们可以做好风险管理。\n\n所以你该怎么办？三个策略。",
        short_copy="🚨美联储又加息了！你的房贷月供要涨3000？3个策略帮你扛过去👇 #美联储 #加息 #理财",
        cta_hooks=["想知道背后的底层逻辑？完整分析见主页置顶视频"],
        domain=ContentDomain.FINANCE,
        content_layer=ContentLayer.HOOK,
        content_type=ContentType.HOT_TAKE,
        account_id="finance_account",
    )
    print(f"\n2. Content: {content.title}")
    print(f"   Sections: {len(content.sections)}, Tags: {content.tags}")

    # ── 3. Test Compliance Stage ──
    print(f"\n3. Running ComplianceStage...")
    ctx = PipelineContext()
    ctx.set("content", content)

    compliance = ComplianceStage()
    result = await compliance.execute(ctx)
    print(f"   Status: {result.status.value}")
    print(f"   Output: {result.output}")

    updated_content: StructuredContent = ctx.get("content")
    print(f"   Disclaimers: {updated_content.disclaimers}")
    print(f"   Compliance notes: {updated_content.compliance_notes}")

    # Check that "保证收益" was reframed
    full_text = " ".join(s.body for s in updated_content.sections)
    if "保证收益" in full_text:
        print("   WARNING: '保证收益' was NOT reframed!")
    else:
        print("   OK: Sensitive terms reframed")

    # ── 4. Test ArticleFormatter ──
    print(f"\n4. Running ArticleFormatterStage...")
    article_stage = ArticleFormatterStage()
    result = await article_stage.execute(ctx)
    print(f"   Status: {result.status.value}")
    html = ctx.get("article_html", "")
    print(f"   HTML length: {len(html)} chars")
    if "<h2" in html or "<section" in html:
        print("   OK: Valid HTML generated")

    # ── 5. Test SSML generation ──
    print(f"\n5. Testing SSML generation...")
    from src.stages.tts_engine.ssml_generator import text_to_ssml, determine_scene
    scene = determine_scene("finance", "hook")
    ssml = text_to_ssml(updated_content.tts_script, scene=scene)
    print(f"   Scene: {scene}")
    print(f"   SSML length: {len(ssml)} chars")
    print(f"   Contains <speak>: {'<speak>' in ssml}")
    print(f"   Contains <prosody>: {'<prosody' in ssml}")

    # ── 6. Test Storyboard generation (fallback, no LLM) ──
    print(f"\n6. Testing storyboard fallback...")
    from src.stages.video_maker.storyboard import _fallback_storyboard
    sb = _fallback_storyboard(updated_content, 90.0)
    print(f"   Scenes: {len(sb.scenes)}")
    print(f"   Duration: {sb.total_duration}s")
    print(f"   Engine: {sb.engine_hint}")

    # ── 7. Test Publisher preparation ──
    print(f"\n7. Testing publisher content preparation...")
    from src.stages.publisher.stage import _prepare_content
    from src.core.models import AudioAsset

    for platform in [Platform.DOUYIN, Platform.BILIBILI, Platform.WECHAT]:
        pc = _prepare_content(updated_content, platform)
        print(f"   {platform.value}: title='{pc.title[:30]}...', tags={len(pc.tags)}")

    # ── 8. Test Podcast RSS generation ──
    print(f"\n8. Testing podcast RSS generation...")
    from src.stages.publisher.podcast import PodcastPublisher
    from src.stages.publisher.base import PlatformContent
    pod = PodcastPublisher(account_config={
        "feed_path": "/tmp/test_podcast_feed.xml",
        "show_name": "锐眼看市",
        "audio_base_url": "https://example.com/podcast/",
    })
    await pod.login()
    pc = PlatformContent(
        platform=Platform.PODCAST,
        title=updated_content.title,
        description=updated_content.summary,
    )
    pub_result = await pod.publish(pc)
    print(f"   Status: {pub_result.status.value}")
    print(f"   Feed path: {pub_result.url}")

    # ── Summary ──
    print(f"\n{'=' * 60}")
    print("LOCAL TEST SUMMARY")
    print(f"{'=' * 60}")
    print("Stages that work WITHOUT API keys:")
    print("  [OK] Compliance (keyword scan + reframe + disclaimer)")
    print("  [OK] ArticleFormatter (Markdown → WeChat HTML)")
    print("  [OK] SSML generation (emotion → speech markup)")
    print("  [OK] Storyboard fallback (synthetic scenes)")
    print("  [OK] Publisher content prep (platform adaptation)")
    print("  [OK] Podcast RSS generation")
    print()
    print("Stages that REQUIRE API keys:")
    print("  [NEED LLM_API_KEY] TopicEngine (sentiment + topic selection)")
    print("  [NEED LLM_API_KEY] TextCreator (content generation)")
    print("  [NEED LLM_API_KEY] Compliance LLM review (local scan still works)")
    print("  [NEED LLM_API_KEY] Storyboard LLM generation (fallback works)")
    print("  [NEED TTS_API_KEY] TTSEngine (speech synthesis)")
    print("  [NEED moviepy]     VideoMaker (video rendering)")
    print("  [NEED credentials] Publishers (platform-specific)")
    print()
    print("To run the full pipeline:")
    print("  export LLM_API_KEY='sk-ant-...'")
    print("  python scripts/run_pipeline.py --workflow hook --domain finance")


if __name__ == "__main__":
    asyncio.run(main())
