from __future__ import annotations

import asyncio
import json
import logging
from datetime import date

import anthropic

from miejskie_trendy.config import MODEL, strip_markdown_fences
from miejskie_trendy.models import Event, RawItem, Source
from miejskie_trendy.prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)


async def group_events(
    items: list[RawItem], today: date | None = None
) -> list[Event]:
    if today is None:
        today = date.today()

    articles = [item.to_dict() for item in items]
    user_message = build_user_message(articles, today.strftime("%Y-%m-%d"))

    logger.info("Sending %d articles to Claude for grouping...", len(items))

    client = anthropic.AsyncAnthropic()
    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            ),
            timeout=120,
        )
    except asyncio.TimeoutError:
        logger.error("Claude API call timed out after 120s")
        return []
    except Exception as e:
        logger.error("Claude API call failed: %s", e)
        return []

    if not response.content:
        logger.error("Claude returned empty response")
        return []

    raw_text = response.content[0].text
    raw_text = strip_markdown_fences(raw_text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Claude response as JSON:\n%s", raw_text[:500])
        return []

    if not isinstance(data, list):
        logger.error("Claude response is not a list: %s", type(data).__name__)
        return []

    events: list[Event] = []
    for entry in data:
        if not isinstance(entry, dict):
            logger.warning("Skipping non-dict entry in Claude response")
            continue

        source_ids = entry.get("source_ids", [])
        sources = []
        for idx in source_ids:
            if isinstance(idx, int) and 0 <= idx < len(items):
                sources.append(Source(
                    title=items[idx].title,
                    url=items[idx].url,
                    published_at=items[idx].published_at,
                ))

        events.append(
            Event(
                id=entry.get("id", ""),
                name=entry.get("name", ""),
                description=entry.get("description", ""),
                category=entry.get("category", "inne"),
                location=entry.get("location"),
                relevance=entry.get("relevance", "medium"),
                confidence=entry.get("confidence", 0.5),
                sources=sources,
            )
        )

    logger.info("Claude identified %d events", len(events))
    return events
