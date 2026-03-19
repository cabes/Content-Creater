"""Platform-specific content rules and adaptation."""
from __future__ import annotations

from src.core.models import Platform

# Platform strictness levels and rules
PLATFORM_RULES = {
    Platform.DOUYIN: {
        "strictness": "high",
        "max_title_length": 30,
        "banned_topics": ["explicit_finance_advice", "superstition"],
        "style": "conservative",
        "notes": "抖音审核严格，神秘学内容需走生活方式路线，金融内容不能有具体投资建议",
    },
    Platform.XIAOHONGSHU: {
        "strictness": "high",
        "max_title_length": 20,
        "banned_topics": ["explicit_finance_advice", "superstition"],
        "style": "lifestyle",
        "notes": "小红书审核严格，内容需要生活化包装，避免硬核术语",
    },
    Platform.BILIBILI: {
        "strictness": "medium",
        "max_title_length": 60,
        "banned_topics": [],
        "style": "academic",
        "notes": "B站相对宽松，可以走学术/知识路线，但也需避免敏感政治内容",
    },
    Platform.WECHAT: {
        "strictness": "medium",
        "max_title_length": 40,
        "banned_topics": [],
        "style": "professional",
        "notes": "公众号适合深度内容，审核中等，注意金融和政治相关合规",
    },
    Platform.YOUTUBE: {
        "strictness": "low",
        "max_title_length": 100,
        "banned_topics": [],
        "style": "free",
        "notes": "YouTube 内容审核相对宽松，但需遵守社区准则",
    },
    Platform.PODCAST: {
        "strictness": "low",
        "max_title_length": 100,
        "banned_topics": [],
        "style": "free",
        "notes": "播客平台审核最宽松",
    },
}


def get_platform_rules(platform: Platform) -> dict:
    """Get rules for a specific platform."""
    return PLATFORM_RULES.get(platform, {"strictness": "medium", "style": "professional"})


def should_use_conservative_version(platform: Platform, domain: str) -> bool:
    """Check if conservative content version should be used for this platform+domain combo."""
    rules = get_platform_rules(platform)
    if rules.get("strictness") == "high":
        return True
    if domain == "mystical" and platform in (Platform.DOUYIN, Platform.XIAOHONGSHU):
        return True
    if domain == "finance" and platform == Platform.DOUYIN:
        return True
    return False
