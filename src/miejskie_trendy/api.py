from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from miejskie_trendy.main import run

logger = logging.getLogger(__name__)

app = FastAPI(title="Miejskie Trendy", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache
_cache: dict = {"events": [], "fetched_at": None}
_cache_ttl_seconds = 900  # 15 minutes
_fetch_lock = asyncio.Lock()


def _cache_is_fresh() -> bool:
    if _cache["fetched_at"] is None:
        return False
    age = (datetime.now(timezone.utc) - _cache["fetched_at"]).total_seconds()
    return age < _cache_ttl_seconds


async def _fetch_events() -> list[dict]:
    async with _fetch_lock:
        # Double-check after acquiring lock
        if _cache_is_fresh():
            return _cache["events"]

        logger.info("Fetching fresh events...")
        events = await run()
        _cache["events"] = events
        _cache["fetched_at"] = datetime.now(timezone.utc)
        logger.info("Cached %d events", len(events))
        return events


@app.get("/api/events")
async def get_events():
    try:
        events = await _fetch_events()
        return {
            "events": events,
            "fetched_at": _cache["fetched_at"].isoformat() if _cache["fetched_at"] else None,
        }
    except Exception as e:
        logger.error("Failed to fetch events: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Nie udało się pobrać wydarzeń", "detail": str(e)},
        )


@app.post("/api/events/refresh")
async def refresh_events():
    _cache["fetched_at"] = None
    try:
        events = await _fetch_events()
        return {
            "events": events,
            "fetched_at": _cache["fetched_at"].isoformat() if _cache["fetched_at"] else None,
        }
    except Exception as e:
        logger.error("Failed to refresh events: %s", e, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Nie udało się odświeżyć wydarzeń", "detail": str(e)},
        )


@app.on_event("startup")
async def _mount_frontend():
    """Mount frontend static files on startup."""
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
