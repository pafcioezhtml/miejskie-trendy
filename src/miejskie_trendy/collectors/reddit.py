from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiohttp

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)

# Public JSON endpoints — no API key needed
SEARCHES = [
    # r/warsaw — all new posts (it's Warsaw-specific already)
    "https://www.reddit.com/r/warsaw/new.json?limit=50",
    # r/polska — search for Warsaw-related posts from today
    "https://www.reddit.com/r/polska/search.json?q=warszawa+OR+warsaw&sort=new&t=day&limit=30",
    # r/poland — English-language posts
    "https://www.reddit.com/r/poland/search.json?q=warsaw+OR+warszawa&sort=new&t=day&limit=20",
]

HEADERS = {
    # Reddit requires a descriptive User-Agent for public API
    "User-Agent": "MiejskieTrendy:v0.1 (event-tracker)",
}


class RedditCollector:
    name = "reddit"

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        seen_ids: set[str] = set()

        async with aiohttp.ClientSession() as session:
            for url in SEARCHES:
                try:
                    posts = await self._fetch(session, url)
                    for post in posts:
                        post_id = post["data"]["id"]
                        if post_id in seen_ids:
                            continue
                        seen_ids.add(post_id)

                        item = self._parse_post(post["data"])
                        if item:
                            items.append(item)
                except Exception:
                    logger.warning("Reddit fetch failed for %s", url, exc_info=True)

        logger.info("Reddit: collected %d items", len(items))
        return items

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> list[dict]:
        async with session.get(url, headers=HEADERS) as resp:
            if resp.status != 200:
                logger.warning("Reddit returned %d for %s", resp.status, url)
                return []
            data = await resp.json()
            return data.get("data", {}).get("children", [])

    def _parse_post(self, data: dict) -> RawItem | None:
        title = data.get("title", "")
        if not title:
            return None

        created_utc = data.get("created_utc")
        published_at = None
        if created_utc:
            published_at = datetime.fromtimestamp(created_utc, tz=timezone.utc)

        selftext = data.get("selftext", "") or ""
        # Truncate long self-posts
        summary = selftext[:300] if selftext else ""

        subreddit = data.get("subreddit", "")
        score = data.get("score", 0)
        num_comments = data.get("num_comments", 0)
        permalink = data.get("permalink", "")
        url = f"https://www.reddit.com{permalink}" if permalink else ""

        return RawItem(
            title=title,
            summary=summary,
            url=url,
            source=self.name,
            published_at=published_at,
            raw_metadata={
                "subreddit": subreddit,
                "score": score,
                "num_comments": num_comments,
                "is_social_media": True,
            },
        )
