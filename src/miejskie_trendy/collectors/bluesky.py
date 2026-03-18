from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiohttp

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)

# Public API — no auth needed for search
SEARCH_URL = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"

QUERIES = ["warszawa", "warsaw"]


class BlueskyCollector:
    name = "bluesky"

    async def collect(self) -> list[RawItem]:
        items: list[RawItem] = []
        seen_uris: set[str] = set()

        async with aiohttp.ClientSession() as session:
            for query in QUERIES:
                try:
                    posts = await self._search(session, query)
                    for post in posts:
                        uri = post.get("uri", "")
                        if uri in seen_uris:
                            continue
                        seen_uris.add(uri)

                        item = self._parse_post(post)
                        if item:
                            items.append(item)
                except Exception:
                    logger.warning(
                        "Bluesky search failed for '%s'", query, exc_info=True
                    )

        logger.info("Bluesky: collected %d items", len(items))
        return items

    async def _search(
        self, session: aiohttp.ClientSession, query: str
    ) -> list[dict]:
        params = {
            "q": query,
            "lang": "pl",
            "limit": "40",
            "sort": "latest",
        }
        async with session.get(SEARCH_URL, params=params) as resp:
            if resp.status != 200:
                logger.warning("Bluesky returned %d for query '%s'", resp.status, query)
                return []
            data = await resp.json()
            return data.get("posts", [])

    def _parse_post(self, post: dict) -> RawItem | None:
        record = post.get("record", {})
        text = record.get("text", "")
        if not text or len(text) < 15:
            return None

        # Parse creation time
        created_at = record.get("createdAt", "")
        published_at = None
        if created_at:
            try:
                # Bluesky uses ISO 8601
                published_at = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError:
                pass

        # Build web URL from author handle and post rkey
        author = post.get("author", {})
        handle = author.get("handle", "")
        uri = post.get("uri", "")
        # URI format: at://did:plc:xxx/app.bsky.feed.post/rkey
        rkey = uri.rsplit("/", 1)[-1] if "/" in uri else ""
        url = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else ""

        display_name = author.get("displayName", handle)
        like_count = post.get("likeCount", 0)
        repost_count = post.get("repostCount", 0)
        reply_count = post.get("replyCount", 0)

        # Use first line as title, rest as summary
        lines = text.strip().split("\n", 1)
        title = lines[0][:120]
        summary = text[:300]

        return RawItem(
            title=title,
            summary=summary,
            url=url,
            source=self.name,
            published_at=published_at,
            raw_metadata={
                "author": display_name,
                "handle": handle,
                "like_count": like_count,
                "repost_count": repost_count,
                "reply_count": reply_count,
                "is_social_media": True,
            },
        )
