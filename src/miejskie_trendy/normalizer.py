from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from miejskie_trendy.models import RawItem

logger = logging.getLogger(__name__)

UTM_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content"}


def _normalize_url(url: str) -> str:
    """Strip tracking params and trailing slashes for dedup."""
    parsed = urlparse(url)
    params = {
        k: v for k, v in parse_qs(parsed.query).items() if k not in UTM_PARAMS
    }
    clean = parsed._replace(
        query=urlencode(params, doseq=True),
        fragment="",
    )
    result = urlunparse(clean).rstrip("/")
    return result


def _is_recent(item: RawItem, cutoff: datetime) -> bool:
    if item.published_at is None:
        # Keep items without a date — let Claude decide
        return True
    dt = item.published_at
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= cutoff


def normalize(
    items: list[RawItem],
    today: date | None = None,
    lookback_hours: int = 24,
) -> list[RawItem]:
    if today is None:
        today = date.today()

    # Cutoff: beginning of today minus lookback buffer
    cutoff = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) - timedelta(
        hours=lookback_hours
    )

    seen_urls: set[str] = set()
    result: list[RawItem] = []

    for item in items:
        # Skip very short titles (likely noise)
        if len(item.title.strip()) < 10:
            continue

        # Date filter — keep articles from last lookback_hours
        if not _is_recent(item, cutoff):
            continue

        # URL dedup
        normalized = _normalize_url(item.url)
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)

        result.append(item)

    logger.info(
        "Normalizer: %d -> %d items (today=%s)", len(items), len(result), today
    )
    return result
