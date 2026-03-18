from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiohttp
import feedparser

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)

RSS_URL = (
    "https://news.google.com/rss/search"
    "?q=Warszawa+when:1d&hl=pl&gl=PL&ceid=PL:pl"
)


class GoogleNewsCollector:
    name = "google_news"

    async def collect(self) -> list[RawItem]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                RSS_URL,
                headers={"User-Agent": "MiejskieTrendy/0.1"},
            ) as resp:
                text = await resp.text()

        feed = feedparser.parse(text)
        items: list[RawItem] = []

        for entry in feed.entries:
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(
                    *entry.published_parsed[:6], tzinfo=timezone.utc
                )

            # Strip HTML from description
            summary = entry.get("summary", "") or ""
            if "<" in summary:
                from bs4 import BeautifulSoup

                summary = BeautifulSoup(summary, "lxml").get_text(separator=" ")

            publisher = ""
            if hasattr(entry, "source") and hasattr(entry.source, "title"):
                publisher = entry.source.title

            items.append(
                RawItem(
                    title=entry.get("title", ""),
                    summary=summary.strip(),
                    url=entry.get("link", ""),
                    source=self.name,
                    published_at=published_at,
                    raw_metadata={"publisher": publisher},
                )
            )

        logger.info("Google News: collected %d items", len(items))
        return items
