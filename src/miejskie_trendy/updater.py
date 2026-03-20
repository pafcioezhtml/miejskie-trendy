"""Updater: collects articles, matches against existing events, updates DB."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timezone
from urllib.parse import urlparse

import anthropic

from miejskie_trendy.collectors.google_news import GoogleNewsCollector
from miejskie_trendy.collectors.reddit import RedditCollector
from miejskie_trendy.collectors.rss import RSSCollector
from miejskie_trendy.collectors.tvn_warszawa import TVNWarszawaCollector
from miejskie_trendy.collectors.um_warszawa import UMWarszawaCollector
from miejskie_trendy.collectors.wykop import WykopCollector
from miejskie_trendy.config import EXTRA_RSS_FEEDS, MODEL, strip_markdown_fences
from miejskie_trendy.db import add_log, get_active_events_summary, upsert_events
from miejskie_trendy.models import RawItem
from miejskie_trendy.normalizer import normalize
from miejskie_trendy.prompt import SYSTEM_PROMPT, MERGE_PROMPT, build_user_message, build_merge_message

logger = logging.getLogger(__name__)


async def _collect_articles(lookback_hours: int = 24) -> list[RawItem]:
    """Run all collectors and normalize."""
    lookback_days = max(1, lookback_hours // 24)
    collectors = [
        GoogleNewsCollector(lookback_days=lookback_days),
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
    failed_count = 0
    for collector, result in zip(collectors, results):
        if isinstance(result, Exception):
            logging.error("Collector %s failed: %s", collector.name, result)
            add_log(f"Kolektor {collector.name}: błąd — {result}", "error")
            failed_count += 1
            continue
        logging.info("Collector %s: %d items", collector.name, len(result))
        add_log(f"Kolektor {collector.name}: {len(result)} artykułów")
        all_items.extend(result)

    if failed_count == len(collectors):
        logger.error("All %d collectors failed — no data available", failed_count)
        add_log(f"UWAGA: wszystkie kolektory ({failed_count}) zakończyły się błędem!", "error")
    elif failed_count > 0:
        logger.warning("%d/%d collectors failed", failed_count, len(collectors))

    normalized = normalize(all_items, lookback_hours=lookback_hours)
    add_log(f"Normalizacja: {len(all_items)} → {len(normalized)} artykułów (lookback {lookback_hours}h)")
    return normalized


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


INITIAL_LOOKBACK_HOURS = 72  # 3 days on first run


async def update() -> int:
    """Full update cycle: collect → match → merge via Claude → save to DB.

    Returns number of active events after update.
    """
    existing = get_active_events_summary()
    is_first_run = len(existing) == 0

    lookback = INITIAL_LOOKBACK_HOURS if is_first_run else 24
    if is_first_run:
        logger.info("First run detected — collecting %d hours of articles", lookback)
        add_log(f"Pierwszy start — zbieranie artykułów z {lookback}h", "info")
    else:
        add_log("Rozpoczynam aktualizację wydarzeń")

    items = await _collect_articles(lookback_hours=lookback)

    if not items:
        logger.warning("No articles collected — skipping update.")
        add_log("Brak artykułów po normalizacji — pomijam", "warning")
        return 0

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
        add_log(f"Tryb merge: {len(existing)} istniejących, {len(items)} nowych artykułów, {len(url_matches)} dopasowań URL")
        system = MERGE_PROMPT
        user_msg = build_merge_message(existing, articles_dicts, today_str)
    else:
        # Fresh mode: no existing events
        logger.info("Fresh mode: %d articles", len(items))
        add_log(f"Tryb fresh: {len(items)} artykułów do analizy")
        system = SYSTEM_PROMPT
        user_msg = build_user_message(articles_dicts, today_str)

    add_log("Wysyłam artykuły do Claude do grupowania...")

    client = anthropic.AsyncAnthropic()
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            ),
            timeout=120,
        )
    except asyncio.TimeoutError:
        logger.error("Claude API call timed out after 120s")
        add_log("Timeout wywołania Claude API (120s)", "error")
        return len(existing)
    except Exception as e:
        logger.error("Claude API call failed: %s", e)
        add_log(f"Błąd wywołania Claude API: {e}", "error")
        return len(existing)

    if not response.content:
        logger.error("Claude returned empty response")
        add_log("Claude zwrócił pustą odpowiedź", "error")
        return len(existing)

    raw_text = strip_markdown_fences(response.content[0].text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Claude response:\n%s", raw_text[:500])
        add_log("Błąd parsowania odpowiedzi Claude", "error")
        return len(existing)

    if not isinstance(data, list):
        logger.error("Claude response is not a list: %s", type(data).__name__)
        add_log("Błąd: odpowiedź Claude nie jest listą JSON", "error")
        return len(existing)

    # Build events with source details
    events_to_save = []
    for entry in data:
        if not isinstance(entry, dict):
            logger.warning("Skipping non-dict entry in Claude response")
            continue

        source_ids = entry.get("source_ids", [])
        sources = []
        for idx in source_ids:
            if isinstance(idx, int) and 0 <= idx < len(items):
                sources.append({
                    "title": items[idx].title,
                    "url": items[idx].url,
                    "published_at": items[idx].published_at.isoformat() if items[idx].published_at else None,
                })

        eid = entry.get("id", "")
        if entry.get("existing_event_id"):
            eid = entry["existing_event_id"]

        if not eid:
            logger.warning("Skipping event with no id: %s", entry.get("name", "?"))
            continue

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

    # In merge mode, don't deactivate events that Claude omitted —
    # they may have been skipped due to token limits, not because they're stale.
    upsert_events(events_to_save, deactivate_missing=not existing)
    logger.info("Update complete: %d events", len(events_to_save))

    # Log each event
    for ev in events_to_save:
        n_src = len(ev.get("sources", []))
        add_log(f"Wydarzenie: {ev['name']} ({n_src} nowych źródeł, {ev.get('category', '?')})")

    add_log(f"Aktualizacja zakończona: {len(events_to_save)} aktywnych wydarzeń")
    return len(events_to_save)
