"""Shared configuration constants."""
from __future__ import annotations

import re

# Extra RSS feeds — easy to add/remove.
# Tuples of (feed_url, collector_name).
EXTRA_RSS_FEEDS = [
    ("https://warsawinsider.pl/feed", "warsaw_insider"),
    ("https://notesfrompoland.com/feed", "notes_from_poland"),
]

# Claude model used for grouping / merging.
MODEL = "claude-sonnet-4-20250514"


def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrapping if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()
