from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import aiohttp

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)

API_BASE = "https://wykop.pl/api/v3"


class WykopCollector:
    """Collector for Wykop.pl — requires WYKOP_KEY and WYKOP_SECRET env vars.

    Free API keys can be obtained at https://dev.wykop.pl/ (requires a Wykop account).
    """

    name = "wykop"

    def __init__(self) -> None:
        self.key = os.environ.get("WYKOP_KEY", "")
        self.secret = os.environ.get("WYKOP_SECRET", "")

    async def collect(self) -> list[RawItem]:
        if not self.key or not self.secret:
            logger.info(
                "Wykop: WYKOP_KEY/WYKOP_SECRET not set — skipping. "
                "Get free API keys at https://dev.wykop.pl/"
            )
            return []

        try:
            token = await self._authenticate()
        except Exception:
            logger.warning("Wykop: authentication failed", exc_info=True)
            return []

        items: list[RawItem] = []
        seen_ids: set[str] = set()

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "MiejskieTrendy/0.1",
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            # 1. Tag #warszawa stream (entries + links)
            tag_items = await self._fetch_tag_stream(session, "warszawa")
            for item in tag_items:
                if item.url not in seen_ids:
                    seen_ids.add(item.url)
                    items.append(item)

            # 2. Search for "warszawa" across entries
            search_items = await self._fetch_search(session, "warszawa")
            for item in search_items:
                if item.url not in seen_ids:
                    seen_ids.add(item.url)
                    items.append(item)

        logger.info("Wykop: collected %d items", len(items))
        return items

    async def _authenticate(self) -> str:
        """Get bearer token using app key+secret."""
        async with aiohttp.ClientSession() as session:
            payload = {"data": {"key": self.key, "secret": self.secret}}
            async with session.post(
                f"{API_BASE}/auth",
                json=payload,
                headers={"User-Agent": "MiejskieTrendy/0.1"},
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(
                        f"Wykop auth failed with status {resp.status}: {text[:200]}"
                    )
                data = await resp.json()
                return data["data"]["token"]

    async def _fetch_tag_stream(
        self, session: aiohttp.ClientSession, tag: str
    ) -> list[RawItem]:
        items: list[RawItem] = []
        try:
            async with session.get(f"{API_BASE}/tags/{tag}/stream") as resp:
                if resp.status != 200:
                    logger.warning("Wykop tag stream returned %d", resp.status)
                    return []
                data = await resp.json()

            for entry in data.get("data", []):
                item = self._parse_entry(entry)
                if item:
                    items.append(item)
        except Exception:
            logger.warning("Wykop tag stream failed", exc_info=True)
        return items

    async def _fetch_search(
        self, session: aiohttp.ClientSession, query: str
    ) -> list[RawItem]:
        items: list[RawItem] = []
        try:
            params = {"q": query}
            async with session.get(
                f"{API_BASE}/search/entries", params=params
            ) as resp:
                if resp.status != 200:
                    logger.warning("Wykop search returned %d", resp.status)
                    return []
                data = await resp.json()

            for entry in data.get("data", []):
                item = self._parse_entry(entry)
                if item:
                    items.append(item)
        except Exception:
            logger.warning("Wykop search failed", exc_info=True)
        return items

    def _parse_entry(self, entry: dict) -> RawItem | None:
        # Entries have "content", links have "title" + "description"
        resource = entry.get("resource", "entry")

        if resource == "link":
            title = entry.get("title", "")
            summary = entry.get("description", "") or ""
            slug = entry.get("slug", "")
            entry_id = entry.get("id", "")
            url = f"https://wykop.pl/link/{entry_id}/{slug}" if entry_id else ""
        else:
            # Entry (mikroblog post)
            content = entry.get("content", "")
            if not content or len(content) < 15:
                return None
            lines = content.strip().split("\n", 1)
            title = lines[0][:120]
            summary = content[:300]
            entry_id = entry.get("id", "")
            url = f"https://wykop.pl/wpis/{entry_id}" if entry_id else ""

        if not title:
            return None

        # Parse date
        created_at = entry.get("created_at", "") or entry.get("published_at", "")
        published_at = None
        if created_at:
            try:
                published_at = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        votes = entry.get("votes", {})
        vote_count = votes.get("up", 0) if isinstance(votes, dict) else 0
        comments_count = entry.get("comments", {}).get("count", 0) if isinstance(entry.get("comments"), dict) else 0

        author = entry.get("author", {})
        username = author.get("username", "") if isinstance(author, dict) else ""

        return RawItem(
            title=title,
            summary=summary,
            url=url,
            source=self.name,
            published_at=published_at,
            raw_metadata={
                "author": username,
                "vote_count": vote_count,
                "comments_count": comments_count,
                "resource_type": resource,
                "is_social_media": True,
            },
        )
