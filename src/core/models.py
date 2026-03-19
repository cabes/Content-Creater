"""Core data models for the content creation pipeline."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────

class ContentLayer(str, enum.Enum):
    HOOK = "hook"      # 情绪流量层 - high frequency, traffic acquisition
    VALUE = "value"    # 认知价值层 - low frequency, trust building


class ContentDomain(str, enum.Enum):
    FINANCE = "finance"           # 财经/商业
    GEOPOLITICS = "geopolitics"   # 地缘政治
    KNOWLEDGE = "knowledge"       # 知识/教育
    MYSTICAL = "mystical"         # 神秘学/灵性修行


class ContentType(str, enum.Enum):
    HOT_TAKE = "hot_take"               # Hook: quick opinion piece
    EMOTION_DECODE = "emotion_decode"    # Hook: emotional analysis
    MYSTICAL_ALERT = "mystical_alert"    # Hook: celestial/mystical alert
    DEEP_ANALYSIS = "deep_analysis"      # Value: in-depth analysis
    FRAMEWORK = "framework"             # Value: cognitive framework
    MYSTICAL_SYSTEM = "mystical_system"  # Value: mystical knowledge system


class PipelineStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Platform(str, enum.Enum):
    BILIBILI = "bilibili"
    WECHAT = "wechat"
    XIAOHONGSHU = "xiaohongshu"
    DOUYIN = "douyin"
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    WEIBO = "weibo"


class EmotionType(str, enum.Enum):
    EXCITED = "excited"
    SERIOUS = "serious"
    TENSE = "tense"
    ANALYTICAL = "analytical"
    MYSTICAL = "mystical"
    MEDITATIVE = "meditative"
    SOLEMN = "solemn"
    HUMOROUS = "humorous"
    WARM = "warm"
    URGENT = "urgent"


# ── Topic Models ───────────────────────────────────────────

class SentimentSignal(BaseModel):
    """Sentiment analysis result from social media scanning."""
    source: str
    topic: str
    emotion_distribution: dict[str, float] = Field(default_factory=dict)  # e.g. {"anger": 0.35, "fear": 0.25}
    intensity: float = Field(ge=0, le=10)
    trend: str = ""  # "polarizing", "rising", "fading"
    emotion_gap: str = ""  # what perspective is missing
    hook_angle: str = ""
    value_angle: str = ""
    raw_sample_count: int = 0
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class Topic(BaseModel):
    """A content topic selected by the topic engine."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    keywords: list[str] = Field(default_factory=list)
    angle: str = ""  # the specific angle/take
    domain: ContentDomain
    content_layer: ContentLayer
    content_type: ContentType
    target_platforms: list[Platform] = Field(default_factory=list)
    account_id: str = ""  # which matrix account to use

    # Scoring
    hook_score: float = 0.0
    value_score: float = 0.0

    # Funnel linkage
    linked_value_topic_id: UUID | None = None  # Hook links to Value topic
    linked_hook_topic_ids: list[UUID] = Field(default_factory=list)  # Value links back to Hooks
    funnel_cta: str = ""  # call-to-action text for funnel

    # Sentiment context
    sentiment_signals: list[SentimentSignal] = Field(default_factory=list)
    emotion_strategy: str = ""  # how to respond to the emotion
    tone: str = ""  # e.g. "冷静权威", "温暖专业"

    # Metadata
    source: str = ""  # where the topic came from
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None  # for time-sensitive topics


# ── Content Models ─────────────────────────────────────────

class EmotionMarker(BaseModel):
    """An emotion annotation within text content."""
    emotion: EmotionType
    text: str
    start_pos: int = 0
    end_pos: int = 0


class VisualCue(BaseModel):
    """Visual direction for a content section."""
    description: str  # what to show visually
    scene_type: str = ""  # chart, flowchart, image, map, symbol_reveal, etc.
    assets_needed: list[str] = Field(default_factory=list)
    duration_hint: float = 0.0  # seconds


class ContentSection(BaseModel):
    """A section of structured content."""
    heading: str = ""
    body: str
    emotion_markers: list[EmotionMarker] = Field(default_factory=list)
    visual_cue: VisualCue | None = None
    tts_script: str = ""  # version optimized for speech
    duration_estimate: float = 0.0  # seconds


class StructuredContent(BaseModel):
    """Full structured content output from text creator."""
    id: UUID = Field(default_factory=uuid4)
    topic_id: UUID
    title: str
    summary: str = ""
    sections: list[ContentSection] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    # Full scripts
    tts_script: str = ""  # full TTS script with emotion markup
    article_text: str = ""  # article version (for WeChat etc.)
    short_copy: str = ""  # short version (for Douyin/Xiaohongshu)

    # CTA / Funnel
    cta_hooks: list[str] = Field(default_factory=list)
    linked_content_ref: str = ""  # reference to linked content
    monetization_anchor: str = ""  # natural product placement

    # Compliance
    disclaimers: list[str] = Field(default_factory=list)
    compliance_notes: str = ""

    # Quality
    quality_score: float = 0.0
    quality_details: dict[str, float] = Field(default_factory=dict)
    iteration_count: int = 0

    # Metadata
    domain: ContentDomain
    content_layer: ContentLayer
    content_type: ContentType
    account_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Audio Models ───────────────────────────────────────────

class AudioTimestamp(BaseModel):
    """A timestamp marker in audio."""
    text: str
    start_time: float  # seconds
    end_time: float
    emotion: EmotionType | None = None


class AudioAsset(BaseModel):
    """Output from TTS engine."""
    id: UUID = Field(default_factory=uuid4)
    content_id: UUID
    file_path: str
    format: str = "mp3"
    duration: float = 0.0  # seconds
    sample_rate: int = 44100
    timestamps: list[AudioTimestamp] = Field(default_factory=list)
    quality_score: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Video Models ───────────────────────────────────────────

class Scene(BaseModel):
    """A single scene in a storyboard."""
    scene_type: str
    description: str
    duration: float
    camera_move: str = "static"
    transition: str = "fade"
    assets_needed: list[str] = Field(default_factory=list)
    text_overlay: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class Storyboard(BaseModel):
    """Full storyboard for video production."""
    id: UUID = Field(default_factory=uuid4)
    content_id: UUID
    scenes: list[Scene] = Field(default_factory=list)
    total_duration: float = 0.0
    aspect_ratio: str = "16:9"
    engine_hint: str = ""  # which rendering engine to use


# ── Publishing Models ──────────────────────────────────────

class PublishResult(BaseModel):
    """Result of publishing to a platform."""
    platform: Platform
    status: PipelineStatus
    url: str = ""
    post_id: str = ""
    error: str = ""
    published_at: datetime | None = None


# ── Pipeline Models ────────────────────────────────────────

class StageResult(BaseModel):
    """Result from a pipeline stage execution."""
    stage_name: str
    status: PipelineStatus
    output: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    duration_seconds: float = 0.0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class PipelineRun(BaseModel):
    """A complete pipeline execution record."""
    id: UUID = Field(default_factory=uuid4)
    workflow_name: str
    topic: Topic | None = None
    content: StructuredContent | None = None
    audio: AudioAsset | None = None
    storyboard: Storyboard | None = None
    publish_results: list[PublishResult] = Field(default_factory=list)
    stage_results: list[StageResult] = Field(default_factory=list)
    status: PipelineStatus = PipelineStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
