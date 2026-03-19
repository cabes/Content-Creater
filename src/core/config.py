"""Configuration management with YAML + environment variable support."""
from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


class LLMConfig(BaseSettings):
    provider: str = "claude"
    model: str = "claude-sonnet-4-20250514"
    api_key: str = ""
    base_url: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7

    model_config = {"env_prefix": "LLM_"}


class RedisConfig(BaseSettings):
    url: str = "redis://localhost:6379/0"

    model_config = {"env_prefix": "REDIS_"}


class DatabaseConfig(BaseSettings):
    url: str = "postgresql+asyncpg://content:content@localhost:5432/content_db"

    model_config = {"env_prefix": "DATABASE_"}


class MinIOConfig(BaseSettings):
    endpoint: str = "localhost:9000"
    access_key: str = "minioadmin"
    secret_key: str = "minioadmin"
    bucket: str = "content-media"
    secure: bool = False

    model_config = {"env_prefix": "MINIO_"}


class TTSConfig(BaseSettings):
    provider: str = "minimax"
    api_key: str = ""
    base_url: str = ""
    default_voice_id: str = ""

    model_config = {"env_prefix": "TTS_"}


class TopicEngineConfig(BaseSettings):
    scan_interval_hours: int = 2
    min_emotion_intensity: float = 7.0
    max_hook_topics_per_scan: int = 5
    dailyhot_url: str = "https://dailyhot.hkg1.zeabur.app"

    model_config = {"env_prefix": "TOPIC_"}


class ComplianceConfig(BaseSettings):
    enabled: bool = True
    auto_fix: bool = True
    max_risk_level: int = 3  # 1-5, reject content above this level

    model_config = {"env_prefix": "COMPLIANCE_"}


class Settings(BaseSettings):
    """Root application settings."""
    app_name: str = "Content Creater"
    debug: bool = False

    llm: LLMConfig = Field(default_factory=LLMConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    minio: MinIOConfig = Field(default_factory=MinIOConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    topic_engine: TopicEngineConfig = Field(default_factory=TopicEngineConfig)
    compliance: ComplianceConfig = Field(default_factory=ComplianceConfig)

    # Paths
    config_dir: Path = CONFIG_DIR
    media_dir: Path = PROJECT_ROOT / "media"
    prompts_dir: Path = CONFIG_DIR / "prompts"

    model_config = {"env_prefix": "APP_"}


def load_yaml_config(path: Path | None = None) -> dict[str, Any]:
    """Load configuration from YAML file."""
    if path is None:
        path = CONFIG_DIR / "config.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings, merging YAML + env vars."""
    yaml_data = load_yaml_config()
    return Settings(**yaml_data)


def get_account_config(account_id: str) -> dict[str, Any]:
    """Load a matrix account configuration."""
    path = CONFIG_DIR / "accounts" / f"{account_id}.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_prompt_template(name: str) -> str:
    """Load a Jinja2 prompt template by name."""
    path = CONFIG_DIR / "prompts" / f"{name}.j2"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text()
