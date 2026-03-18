"""Background scheduler for periodic event updates."""
from __future__ import annotations

import asyncio
import logging
import os

from miejskie_trendy.updater import update

logger = logging.getLogger(__name__)


async def run_scheduler() -> None:
    """Run update loop in the background. First run is immediate if DB is empty."""
    interval_minutes = int(os.environ.get("UPDATE_INTERVAL_MINUTES", "60"))
    interval_seconds = interval_minutes * 60

    logger.info("Scheduler started (interval: %d minutes)", interval_minutes)

    # Immediate first run
    await _run_update_safe()

    while True:
        await asyncio.sleep(interval_seconds)
        await _run_update_safe()


async def _run_update_safe() -> None:
    try:
        count = await update()
        logger.info("Scheduled update complete: %d active events", count)
    except Exception:
        logger.error("Scheduled update failed", exc_info=True)
