from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from miejskie_trendy.db import get_active_events, get_last_update_time, init_db
from miejskie_trendy.scheduler import run_scheduler

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler_task

    # Init database
    init_db()

    # Mount frontend
    _mount_frontend(app)

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
    from miejskie_trendy.updater import update

    try:
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
