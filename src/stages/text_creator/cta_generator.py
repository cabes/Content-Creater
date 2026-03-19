"""CTA (Call-to-Action) and funnel text generator."""
from __future__ import annotations

from src.core.models import ContentDomain, ContentLayer

# CTA templates by domain and layer
CTA_TEMPLATES = {
    ("finance", "hook"): [
        "想知道背后的底层逻辑？完整分析见主页置顶视频",
        "这只是冰山一角，万字深度拆解链接在评论区",
        "关注我，每天带你看懂财经真相",
    ],
    ("finance", "value"): [
        "如果你想系统学习这套分析框架，我的投研社群每周都有实战练习",
        "想要一对一讨论你的资产配置方案？评论区留言或私信",
    ],
    ("geopolitics", "hook"): [
        "想深入了解这场博弈的来龙去脉？完整版分析见主页",
        "关注我，带你看透国际局势的底层逻辑",
    ],
    ("geopolitics", "value"): [
        "更多深度分析，欢迎关注公众号获取完整版",
    ],
    ("mystical", "hook"): [
        "想知道这次天象对你星座的具体影响？详细解读见主页",
        "关注我，每周天象预报不错过",
        "你的星盘里也藏着类似的能量模式，私信我了解",
    ],
    ("mystical", "value"): [
        "如果你想系统学习古典占星，我的21天入门课正在招募",
        "我们的灵性成长社群每周共修，欢迎加入",
        "想要个人星盘深度解读？详情见主页置顶",
    ],
    ("knowledge", "hook"): [
        "完整版深度解析见主页，带你建立系统认知",
        "关注我，用第一性原理拆解复杂问题",
    ],
    ("knowledge", "value"): [
        "如果觉得有收获，点个关注，我们下期继续深挖",
    ],
}


def get_cta_for_content(
    domain: ContentDomain,
    layer: ContentLayer,
    count: int = 2,
) -> list[str]:
    """Get CTA hooks for content based on domain and layer."""
    key = (domain.value, layer.value)
    templates = CTA_TEMPLATES.get(key, CTA_TEMPLATES.get(("knowledge", layer.value), []))
    return templates[:count]


def generate_cross_promote_cta(
    source_domain: ContentDomain,
    target_domain: ContentDomain,
) -> str:
    """Generate cross-promotion CTA between accounts."""
    cross_promote = {
        ("geopolitics", "finance"): "这场冲突对投资市场的影响，详见@{finance_account}的深度分析",
        ("finance", "mystical"): "除了基本面分析，从占星周期看这轮行情...详见@{mystical_account}",
        ("geopolitics", "mystical"): "从更宏观的周期来看这场变局...@{mystical_account}",
        ("mystical", "finance"): "这个星象周期在历史上往往对应经济转折点...详见@{finance_account}",
    }
    key = (source_domain.value, target_domain.value)
    return cross_promote.get(key, "")
