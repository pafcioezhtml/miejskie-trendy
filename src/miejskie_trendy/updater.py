"""Updater: collects articles, matches against existing events, updates DB."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date, datetime, timezone
from urllib.parse import urlparse

import anthropic

from miejskie_trendy.collectors.google_news import GoogleNewsCollector
from miejskie_trendy.collectors.reddit import RedditCollector
from miejskie_trendy.collectors.rss import RSSCollector
from miejskie_trendy.collectors.tvn_warszawa import TVNWarszawaCollector
from miejskie_trendy.collectors.um_warszawa import UMWarszawaCollector
from miejskie_trendy.collectors.wykop import WykopCollector
from miejskie_trendy.db import get_active_events_summary, upsert_events
from miejskie_trendy.models import RawItem
from miejskie_trendy.normalizer import normalize
from miejskie_trendy.prompt import SYSTEM_PROMPT, MERGE_PROMPT, build_user_message, build_merge_message

logger = logging.getLogger(__name__)

EXTRA_RSS_FEEDS = [
    ("https://warsawinsider.pl/feed", "warsaw_insider"),
    ("https://notesfrompoland.com/feed", "notes_from_poland"),
]

MODEL = "claude-sonnet-4-20250514"


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


async def _collect_articles() -> list[RawItem]:
    """Run all collectors and normalize."""
    collectors = [
        GoogleNewsCollector(),
        TVNWarszawaCollector(),
        UMWarszawaCollector(),
        RedditCollector(),
        WykopCollector(),
        *[RSSCollector(url, name) for url, name in EXTRA_RSS_FEEDS],
    ]

    results = await asyncio.gather(
        *[c.collect() for c in collectors],
        return_exceptions=True,
    )

    all_items: list[RawItem] = []
    for collector, result in zip(collectors, results):
        if isinstance(result, Exception):
            logging.error("Collector %s failed: %s", collector.name, result)
            continue
        logging.info("Collector %s: %d items", collector.name, len(result))
        all_items.extend(result)

    return normalize(all_items)


def _match_by_url_overlap(
    new_article_urls: set[str],
    existing_events: list[dict],
) -> dict[str, str]:
    """Pre-match new articles to existing events by source URL overlap.

    Returns mapping: existing_event_id → comma-separated matching article indices.
    """
    matches: dict[str, list[str]] = {}
    for ev in existing_events:
        ev_urls = set()
        for url in ev.get("source_urls", []):
            parsed = urlparse(url)
            # Normalize: strip scheme, www, trailing slash
            normalized = parsed.netloc.removeprefix("www.") + parsed.path.rstrip("/")
            ev_urls.add(normalized)

        overlap = ev_urls & new_article_urls
        if overlap:
            matches[ev["id"]] = list(overlap)

    return matches


async def update() -> int:
    """Full update cycle: collect → match → merge via Claude → save to DB.

    Returns number of active events after update.
    """
    items = await _collect_articles()

    if not items:
        logger.warning("No articles collected — skipping update.")
        return 0

    existing = get_active_events_summary()

    # Build normalized URL set for matching
    article_urls_normalized = set()
    for item in items:
        parsed = urlparse(item.url)
        normalized = parsed.netloc.removeprefix("www.") + parsed.path.rstrip("/")
        article_urls_normalized.add(normalized)

    url_matches = _match_by_url_overlap(article_urls_normalized, existing)

    # Choose prompt based on whether we have existing events
    articles_dicts = [item.to_dict() for item in items]
    today_str = date.today().strftime("%Y-%m-%d")

    if existing:
        # Merge mode: send existing events + new articles
        logger.info(
            "Merge mode: %d existing events, %d new articles, %d URL overlaps",
            len(existing), len(items), len(url_matches),
        )
        system = MERGE_PROMPT
        user_msg = build_merge_message(existing, articles_dicts, today_str)
    else:
        # Fresh mode: no existing events
        logger.info("Fresh mode: %d articles", len(items))
        system = SYSTEM_PROMPT
        user_msg = build_user_message(articles_dicts, today_str)

    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw_text = _strip_markdown_fences(response.content[0].text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Claude response:\n%s", raw_text[:500])
        return len(existing)

    # Build events with source details
    events_to_save = []
    for entry in data:
        source_ids = entry.get("source_ids", [])
        sources = []
        for idx in source_ids:
            if 0 <= idx < len(items):
                sources.append({
                    "title": items[idx].title,
                    "url": items[idx].url,
                    "published_at": items[idx].published_at.isoformat() if items[idx].published_at else None,
                })

        # Also keep existing sources if event was matched
        eid = entry.get("id", "")
        if entry.get("existing_event_id"):
            eid = entry["existing_event_id"]

        events_to_save.append({
            "id": eid,
            "name": entry.get("name", ""),
            "description": entry.get("description", ""),
            "category": entry.get("category", "inne"),
            "location": entry.get("location"),
            "relevance": entry.get("relevance", "medium"),
            "confidence": entry.get("confidence", 0.5),
            "sources": sources,
        })

    upsert_events(events_to_save)
    logger.info("Update complete: %d events", len(events_to_save))
    return len(events_to_save)
