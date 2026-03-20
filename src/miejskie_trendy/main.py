from __future__ import annotations

import asyncio
import json
import logging
import sys

from dotenv import load_dotenv

from miejskie_trendy.collectors.google_news import GoogleNewsCollector
from miejskie_trendy.collectors.reddit import RedditCollector
from miejskie_trendy.collectors.rss import RSSCollector
from miejskie_trendy.collectors.tvn_warszawa import TVNWarszawaCollector
from miejskie_trendy.collectors.um_warszawa import UMWarszawaCollector
from miejskie_trendy.collectors.wykop import WykopCollector
from miejskie_trendy.config import EXTRA_RSS_FEEDS
from miejskie_trendy.grouper import group_events
from miejskie_trendy.models import RawItem
from miejskie_trendy.normalizer import normalize


async def run() -> list[dict]:
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

    items = normalize(all_items)

    if not items:
        logging.warning("No items after normalization — nothing to group.")
        return []

    events = await group_events(items)
    return [e.to_dict() for e in events]


def main():
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    events = asyncio.run(run())
    output = json.dumps(events, ensure_ascii=False, indent=2)
    print(output)


if __name__ == "__main__":
    main()
