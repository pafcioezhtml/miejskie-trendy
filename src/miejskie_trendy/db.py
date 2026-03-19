from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_DB_PATH: str | None = None


def _get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = os.environ.get("DATABASE_PATH", "data/events.db")
    return _DB_PATH


def get_connection() -> sqlite3.Connection:
    path = _get_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                location TEXT,
                relevance TEXT NOT NULL DEFAULT 'medium',
                confidence REAL NOT NULL DEFAULT 0.5,
                first_seen_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL REFERENCES events(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at TEXT,
                UNIQUE(event_id, url)
            );

            CREATE INDEX IF NOT EXISTS idx_events_active ON events(is_active);
            CREATE INDEX IF NOT EXISTS idx_sources_event ON sources(event_id);

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL DEFAULT 'info',
                message TEXT NOT NULL
            );
        """)
        conn.commit()
        logger.info("Database initialized at %s", _get_db_path())
    finally:
        conn.close()


def get_active_events() -> list[dict]:
    """Read all active events with their sources."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM events WHERE is_active = 1 ORDER BY last_updated_at DESC"
        ).fetchall()

        events = []
        for row in rows:
            sources = conn.execute(
                "SELECT title, url, published_at FROM sources WHERE event_id = ? "
                "ORDER BY published_at DESC NULLS LAST",
                (row["id"],),
            ).fetchall()

            events.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "location": row["location"],
                "relevance": row["relevance"],
                "confidence": row["confidence"],
                "first_seen_at": row["first_seen_at"],
                "last_updated_at": row["last_updated_at"],
                "sources": [
                    {
                        "title": s["title"],
                        "url": s["url"],
                        "published_at": s["published_at"],
                    }
                    for s in sources
                ],
            })
        return events
    finally:
        conn.close()


def get_active_events_summary() -> list[dict]:
    """Compact summary for the merge prompt — just id, name, description, source URLs."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, name, description, category, location FROM events WHERE is_active = 1"
        ).fetchall()

        result = []
        for row in rows:
            source_urls = [
                r["url"]
                for r in conn.execute(
                    "SELECT url FROM sources WHERE event_id = ?", (row["id"],)
                ).fetchall()
            ]
            result.append({
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "category": row["category"],
                "location": row["location"],
                "source_urls": source_urls,
            })
        return result
    finally:
        conn.close()


def upsert_events(events: list[dict], now: str | None = None) -> None:
    """Insert or update events. Deactivate events not in the new list."""
    if now is None:
        now = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        new_ids = set()
        for ev in events:
            eid = ev["id"]
            new_ids.add(eid)

            # Check if exists
            existing = conn.execute(
                "SELECT id, first_seen_at FROM events WHERE id = ?", (eid,)
            ).fetchone()

            if existing:
                conn.execute(
                    """UPDATE events SET
                        name = ?, description = ?, category = ?, location = ?,
                        relevance = ?, confidence = ?, last_updated_at = ?, is_active = 1
                    WHERE id = ?""",
                    (
                        ev["name"], ev["description"], ev["category"],
                        ev.get("location"), ev["relevance"], ev["confidence"],
                        now, eid,
                    ),
                )
            else:
                conn.execute(
                    """INSERT INTO events
                        (id, name, description, category, location, relevance,
                         confidence, first_seen_at, last_updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        eid, ev["name"], ev["description"], ev["category"],
                        ev.get("location"), ev["relevance"], ev["confidence"],
                        now, now,
                    ),
                )

            # Upsert sources
            for src in ev.get("sources", []):
                conn.execute(
                    """INSERT INTO sources (event_id, title, url, published_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(event_id, url) DO UPDATE SET
                        title = excluded.title,
                        published_at = excluded.published_at""",
                    (eid, src["title"], src["url"], src.get("published_at")),
                )

        # Deactivate events not returned by this run
        if new_ids:
            placeholders = ",".join("?" for _ in new_ids)
            conn.execute(
                f"UPDATE events SET is_active = 0, last_updated_at = ? "
                f"WHERE is_active = 1 AND id NOT IN ({placeholders})",
                [now, *new_ids],
            )

        conn.commit()
        logger.info("DB updated: %d active events", len(new_ids))
    finally:
        conn.close()


def reset_db() -> None:
    """Drop all data — triggers fresh 3-day collection on next update."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM sources")
        conn.execute("DELETE FROM events")
        conn.commit()
        logger.info("Database reset — all events cleared")
    finally:
        conn.close()


def get_last_update_time() -> str | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT MAX(last_updated_at) as t FROM events WHERE is_active = 1"
        ).fetchone()
        return row["t"] if row else None
    finally:
        conn.close()


# --- Settings ---

_SETTINGS_DEFAULTS = {
    "update_interval_minutes": "60",
    "update_enabled": "true",
    "anthropic_api_key": "",
    "wykop_key": "",
    "wykop_secret": "",
}


def get_settings() -> dict[str, str]:
    """Get all settings, merged with defaults."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        stored = {r["key"]: r["value"] for r in rows}
        result = {**_SETTINGS_DEFAULTS, **stored}
        return result
    finally:
        conn.close()


def get_setting(key: str) -> str:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        if row:
            return row["value"]
        return _SETTINGS_DEFAULTS.get(key, "")
    finally:
        conn.close()


def save_settings(settings: dict[str, str]) -> None:
    conn = get_connection()
    try:
        for key, value in settings.items():
            if key in _SETTINGS_DEFAULTS:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )
        conn.commit()
        logger.info("Settings saved: %s", list(settings.keys()))
    finally:
        conn.close()


# --- Logs ---

MAX_LOG_ENTRIES = 500


def add_log(message: str, level: str = "info") -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO logs (timestamp, level, message) VALUES (?, ?, ?)",
            (now, level, message),
        )
        # Trim old entries
        conn.execute(
            "DELETE FROM logs WHERE id NOT IN "
            "(SELECT id FROM logs ORDER BY id DESC LIMIT ?)",
            (MAX_LOG_ENTRIES,),
        )
        conn.commit()
    finally:
        conn.close()


def get_logs(limit: int = 100) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT timestamp, level, message FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
