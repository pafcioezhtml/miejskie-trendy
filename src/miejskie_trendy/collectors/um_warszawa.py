from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import aiohttp
from bs4 import BeautifulSoup

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)

PAGE_URL = "https://um.warszawa.pl/waw/warszawa/aktualnosci"

DATE_RE = re.compile(r"\d{2}\.\d{2}\.\d{4}")


class UMWarszawaCollector:
    name = "um_warszawa"

    async def collect(self) -> list[RawItem]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                PAGE_URL,
                headers={"User-Agent": "MiejskieTrendy/0.1"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    logger.warning("um.warszawa.pl returned HTTP %d", resp.status)
                    return []
                html = await resp.text()

        soup = BeautifulSoup(html, "lxml")
        items: list[RawItem] = []

        # um.warszawa.pl uses article-like cards with links and dates.
        # We try multiple selectors to be resilient to layout changes.
        articles = (
            soup.select("article")
            or soup.select(".news-item")
            or soup.select(".asset-entry")
        )

        # Fallback: look for any links that look like news articles
        if not articles:
            articles = []
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                if "/aktualnosci/" in href or "/news/" in href:
                    # Use the parent container as the "article"
                    parent = a_tag.find_parent(["li", "div", "article"])
                    if parent and parent not in articles:
                        articles.append(parent)

        for article in articles:
            try:
                item = self._parse_article(article)
                if item:
                    items.append(item)
            except Exception:
                logger.debug("Failed to parse article element", exc_info=True)
                continue

        logger.info("um.warszawa.pl: collected %d items", len(items))
        return items

    def _parse_article(self, element) -> RawItem | None:
        # Find the main link
        a_tag = element.find("a", href=True)
        if not a_tag:
            return None

        href = a_tag["href"]
        if not href.startswith("http"):
            href = "https://um.warszawa.pl" + href

        title = a_tag.get_text(strip=True)
        if not title or len(title) < 5:
            return None

        # Try to extract date
        text = element.get_text(" ", strip=True)
        published_at = None
        date_match = DATE_RE.search(text)
        if date_match:
            try:
                published_at = datetime.strptime(date_match.group(), "%d.%m.%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        # Extract summary (text minus the title and date)
        summary = text.replace(title, "").strip()
        if date_match:
            summary = summary.replace(date_match.group(), "").strip()
        # Clean up multiple spaces
        summary = re.sub(r"\s+", " ", summary)[:300]

        return RawItem(
            title=title,
            summary=summary,
            url=href,
            source=self.name,
            published_at=published_at,
            raw_metadata={},
        )
