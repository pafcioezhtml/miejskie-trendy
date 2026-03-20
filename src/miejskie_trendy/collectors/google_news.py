from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone

import aiohttp
import feedparser

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)

# Google News returns max ~100 results per query, so for multi-day
# lookback we issue separate queries with date ranges (before:/after:).
BASE_URL = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=pl&gl=PL&ceid=PL:pl"
)


class GoogleNewsCollector:
    name = "google_news"

    def __init__(self, lookback_days: int = 1) -> None:
        self.lookback_days = lookback_days

    async def collect(self) -> list[RawItem]:
        if self.lookback_days <= 1:
            queries = ["Warszawa+when:1d"]
        else:
            # Build per-day queries to avoid 100-result limit
            queries = []
            today = date.today()
            for i in range(self.lookback_days):
                day = today - timedelta(days=i)
                after = day.strftime("%Y-%m-%d")
                before = (day + timedelta(days=1)).strftime("%Y-%m-%d")
                queries.append(f"Warszawa+after:{after}+before:{before}")

        all_items: list[RawItem] = []
        seen_urls: set[str] = set()

        async with aiohttp.ClientSession() as session:
            for query in queries:
                url = BASE_URL.format(query=query)
                try:
                    items = await self._fetch_feed(session, url)
                    for item in items:
                        if item.url not in seen_urls:
                            seen_urls.add(item.url)
                            all_items.append(item)
                except Exception:
                    logger.warning("Google News query failed: %s", query, exc_info=True)

        logger.info(
            "Google News: collected %d items (%d days, %d queries)",
            len(all_items), self.lookback_days, len(queries),
        )
        return all_items

    async def _fetch_feed(
        self, session: aiohttp.ClientSession, url: str
    ) -> list[RawItem]:
        async with session.get(
            url,
            headers={"User-Agent": "MiejskieTrendy/0.1"},
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            if resp.status != 200:
                logger.warning("Google News returned HTTP %d for %s", resp.status, url)
                return []
            text = await resp.text()

        feed = feedparser.parse(text)
        items: list[RawItem] = []

        for entry in feed.entries:
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(
                    *entry.published_parsed[:6], tzinfo=timezone.utc
                )

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

        return items
