from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiohttp
import feedparser

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)


class RSSCollector:
    """Universal RSS collector — pass any feed URL and a name."""

    def __init__(self, feed_url: str, name: str) -> None:
        self.feed_url = feed_url
        self.name = name

    async def collect(self) -> list[RawItem]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.feed_url,
                    headers={"User-Agent": "MiejskieTrendy/0.1"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "%s: HTTP %d from %s", self.name, resp.status, self.feed_url
                        )
                        return []
                    text = await resp.text()
        except Exception:
            logger.warning("%s: fetch failed for %s", self.name, self.feed_url, exc_info=True)
            return []

        feed = feedparser.parse(text)
        items: list[RawItem] = []

        for entry in feed.entries:
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(
                    *entry.published_parsed[:6], tzinfo=timezone.utc
                )

            summary = entry.get("summary", "") or entry.get("description", "") or ""
            if "<" in summary:
                from bs4 import BeautifulSoup
                summary = BeautifulSoup(summary, "lxml").get_text(separator=" ")

            items.append(
                RawItem(
                    title=entry.get("title", ""),
                    summary=summary.strip()[:300],
                    url=entry.get("link", ""),
                    source=self.name,
                    published_at=published_at,
                    raw_metadata={},
                )
            )

        logger.info("%s: collected %d items from %s", self.name, len(items), self.feed_url)
        return items
