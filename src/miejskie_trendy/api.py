from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from miejskie_trendy.db import (
    get_active_events, get_last_update_time, get_logs, get_settings,
    init_db, reset_db, save_settings,
)
from miejskie_trendy.scheduler import notify_settings_changed, run_scheduler

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None
_last_refresh_time: float = 0
_REFRESH_COOLDOWN_SECONDS = 60


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task

    # Init database
    init_db()

    # Mount frontend
    _mount_frontend(app)

    # Apply API keys from settings to env (so SDKs pick them up)
    _apply_key_settings()

    # Start background scheduler
    _scheduler_task = asyncio.create_task(run_scheduler())
    logger.info("Background scheduler started")

    yield

    # Shutdown
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Miejskie Trendy", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _apply_key_settings():
    """Override env vars with API keys stored in DB settings (if non-empty)."""
    settings = get_settings()
    key_map = {
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "wykop_key": "WYKOP_KEY",
        "wykop_secret": "WYKOP_SECRET",
    }
    for setting_key, env_var in key_map.items():
        val = settings.get(setting_key, "")
        if val:
            os.environ[env_var] = val


def _mount_frontend(app: FastAPI):
    """Mount frontend static files."""
    candidates = [
        os.environ.get("FRONTEND_DIST"),
        str(Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"),
        "/app/frontend/dist",
    ]
    for path in candidates:
        if path and Path(path).is_dir() and (Path(path) / "index.html").exists():
            app.mount("/", StaticFiles(directory=path, html=True), name="frontend")
            logger.info("Serving frontend from %s", path)
            return
    logger.warning("Frontend dist not found — API-only mode")


@app.get("/api/events")
async def get_events():
    try:
        events = get_active_events()
        last_update = get_last_update_time()
        return {
            "events": events,
            "fetched_at": last_update,
        }
    except Exception as e:
        logger.error("Failed to get events: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Nie udało się pobrać wydarzeń", "detail": str(e)},
        )


@app.post("/api/events/refresh")
async def refresh_events():
    """Trigger an immediate update."""
    global _last_refresh_time

    now = time.monotonic()
    elapsed = now - _last_refresh_time
    if elapsed < _REFRESH_COOLDOWN_SECONDS:
        remaining = int(_REFRESH_COOLDOWN_SECONDS - elapsed)
        return JSONResponse(
            status_code=429,
            content={"error": f"Odczekaj {remaining}s przed kolejnym odświeżeniem"},
        )

    from miejskie_trendy.updater import update

    try:
        _last_refresh_time = now
        count = await update()
        events = get_active_events()
        last_update = get_last_update_time()
        return {
            "events": events,
            "fetched_at": last_update,
        }
    except Exception as e:
        logger.error("Failed to refresh events: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Nie udało się odświeżyć wydarzeń", "detail": str(e)},
        )


@app.post("/api/events/rebuild")
async def rebuild_events():
    """Clear DB and do a fresh 3-day collection."""
    global _last_refresh_time

    now = time.monotonic()
    elapsed = now - _last_refresh_time
    if elapsed < _REFRESH_COOLDOWN_SECONDS:
        remaining = int(_REFRESH_COOLDOWN_SECONDS - elapsed)
        return JSONResponse(
            status_code=429,
            content={"error": f"Odczekaj {remaining}s przed kolejnym odświeżeniem"},
        )

    from miejskie_trendy.updater import update

    try:
        _last_refresh_time = now
        reset_db()
        count = await update()
        events = get_active_events()
        last_update = get_last_update_time()
        return {
            "events": events,
            "fetched_at": last_update,
        }
    except Exception as e:
        logger.error("Failed to rebuild events: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Nie udało się przebudować bazy", "detail": str(e)},
        )


@app.get("/api/settings")
async def api_get_settings():
    settings = get_settings()
    # Mask API keys for display (show last 4 chars only)
    for key in ("anthropic_api_key", "wykop_key", "wykop_secret"):
        val = settings.get(key, "")
        if val and len(val) > 4:
            settings[key] = "***" + val[-4:]
    return settings


@app.get("/api/logs")
async def api_get_logs():
    return get_logs(200)


_API_KEY_FIELDS = {"anthropic_api_key", "wykop_key", "wykop_secret"}


@app.put("/api/settings")
async def api_save_settings(body: dict):
    # Don't save masked values; don't allow clearing API keys via empty string
    to_save = {}
    for key, value in body.items():
        if isinstance(value, str) and value.startswith("***"):
            continue  # masked — no change
        if key in _API_KEY_FIELDS and not value:
            continue  # don't clear API keys via empty string
        to_save[key] = value if value else ""
    save_settings(to_save)
    _apply_key_settings()
    notify_settings_changed()
    return {"ok": True}


def start():
    import uvicorn

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    start()
