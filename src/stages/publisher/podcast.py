"""Podcast publisher - generates RSS feed and manages audio hosting."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.core.models import Platform, PublishResult, PipelineStatus
from .base import BasePublisher, PlatformContent

logger = structlog.get_logger()


class PodcastPublisher(BasePublisher):
    """Generate and update podcast RSS feed."""

    platform = Platform.PODCAST
    name = "podcast"

    def __init__(self, account_config: dict[str, Any] | None = None, **kwargs: Any):
        super().__init__(account_config, **kwargs)
        self.feed_path = Path(self.account_config.get("feed_path", "media/podcast/feed.xml"))
        self.audio_base_url = self.account_config.get("audio_base_url", "https://example.com/podcast/")
        self.show_name = self.account_config.get("show_name", "Content Creater Podcast")
        self.show_description = self.account_config.get("show_description", "")

    async def login(self) -> bool:
        """No login needed for RSS feed generation."""
        self._logged_in = True
        return True

    async def publish(self, content: PlatformContent) -> PublishResult:
        try:
            self.feed_path.parent.mkdir(parents=True, exist_ok=True)

            # Load existing feed or create new
            if self.feed_path.exists():
                tree = ET.parse(str(self.feed_path))
                root = tree.getroot()
                channel = root.find("channel")
            else:
                root = ET.Element("rss", version="2.0")
                root.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
                channel = ET.SubElement(root, "channel")
                ET.SubElement(channel, "title").text = self.show_name
                ET.SubElement(channel, "description").text = self.show_description
                ET.SubElement(channel, "language").text = "zh-cn"
                tree = ET.ElementTree(root)

            if channel is None:
                channel = ET.SubElement(root, "channel")

            # Add new episode
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = content.title
            ET.SubElement(item, "description").text = content.description
            ET.SubElement(item, "pubDate").text = datetime.utcnow().strftime(
                "%a, %d %b %Y %H:%M:%S +0000"
            )

            if content.audio_path:
                audio_filename = Path(content.audio_path).name
                enclosure = ET.SubElement(item, "enclosure")
                enclosure.set("url", f"{self.audio_base_url}{audio_filename}")
                enclosure.set("type", "audio/mpeg")
                audio_size = Path(content.audio_path).stat().st_size if Path(content.audio_path).exists() else 0
                enclosure.set("length", str(audio_size))

            # Write feed
            tree.write(str(self.feed_path), encoding="unicode", xml_declaration=True)

            logger.info("podcast.episode_added", title=content.title)

            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.COMPLETED,
                url=str(self.feed_path),
            )

        except Exception as e:
            logger.exception("podcast.publish_failed")
            return PublishResult(
                platform=self.platform,
                status=PipelineStatus.FAILED,
                error=str(e),
            )
