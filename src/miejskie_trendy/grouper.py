from __future__ import annotations

import json
import logging
import re
from datetime import date

import anthropic

from miejskie_trendy.models import Event, RawItem, Source
from miejskie_trendy.prompt import SYSTEM_PROMPT, build_user_message

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrapping if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()


async def group_events(
    items: list[RawItem], today: date | None = None
) -> list[Event]:
    if today is None:
        today = date.today()

    articles = [item.to_dict() for item in items]
    user_message = build_user_message(articles, today.strftime("%Y-%m-%d"))

    logger.info("Sending %d articles to Claude for grouping...", len(items))

    client = anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text
    raw_text = _strip_markdown_fences(raw_text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Claude response as JSON:\n%s", raw_text[:500])
        return []

    events: list[Event] = []
    for entry in data:
        source_ids = entry.get("source_ids", [])
        sources = []
        for idx in source_ids:
            if 0 <= idx < len(items):
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
