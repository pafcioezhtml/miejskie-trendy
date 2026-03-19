"""Background scheduler for periodic event updates."""
from __future__ import annotations

import asyncio
import logging
import os

from miejskie_trendy.db import get_setting
from miejskie_trendy.updater import update

logger = logging.getLogger(__name__)

# Event to signal scheduler to re-read settings
settings_changed = asyncio.Event()


def notify_settings_changed() -> None:
    """Call after saving settings to wake up the scheduler."""
    settings_changed.set()


async def run_scheduler() -> None:
    """Run update loop. Re-reads interval and enabled flag from DB each cycle."""

    # Immediate first run
    await _run_update_safe()

    while True:
        interval = _get_interval()
        enabled = _is_enabled()

        if not enabled:
            logger.info("Scheduler paused — waiting for settings change")
            settings_changed.clear()
            await settings_changed.wait()
            continue

        logger.debug("Scheduler sleeping %d minutes", interval)
        settings_changed.clear()

        # Wait for either the interval or a settings change
        try:
            await asyncio.wait_for(settings_changed.wait(), timeout=interval * 60)
            # Settings changed — loop back to re-read them
            logger.info("Scheduler woke up — settings changed")
            continue
        except asyncio.TimeoutError:
            # Normal interval elapsed — run update
            pass

        if _is_enabled():
            await _run_update_safe()


def _get_interval() -> int:
    try:
        return int(get_setting("update_interval_minutes"))
    except (ValueError, TypeError):
        return int(os.environ.get("UPDATE_INTERVAL_MINUTES", "60"))


def _is_enabled() -> bool:
    return get_setting("update_enabled").lower() in ("true", "1", "yes")


async def _run_update_safe() -> None:
    try:
        count = await update()
        logger.info("Scheduled update complete: %d active events", count)
    except Exception:
        logger.error("Scheduled update failed", exc_info=True)
