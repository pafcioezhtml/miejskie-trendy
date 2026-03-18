# Miejskie Trendy

Warsaw city events tracker — collects news articles and social media posts about events affecting Warsaw residents, groups them using Claude AI, and displays them in a web UI.

## Architecture

```
[Collectors] → [Normalizer] → [Claude Sonnet Grouper] → [FastAPI] → [React Frontend]
```

**Pipeline:** Async collectors gather raw articles in parallel → normalizer deduplicates and filters to last 24h → Claude Sonnet selects relevant city events, groups related articles, extracts locations → JSON output.

**Key design decision:** The Claude prompt in `prompt.py` is the primary configuration for what counts as a "city event." Changing the scope (e.g., only transport, only culture) means editing the prompt text, not the code.

## Project Structure

```
src/miejskie_trendy/
├── main.py              # CLI entry point, orchestrates pipeline, run() returns list[dict]
├── api.py               # FastAPI server, serves /api/events + static frontend
├── models.py            # RawItem, Source, Event dataclasses
├── normalizer.py        # URL dedup, date filtering (24h lookback)
├── grouper.py           # Claude Sonnet API call, parses JSON response into Events
├── prompt.py            # System prompt + user message builder (MOST IMPORTANT FILE for tuning)
└── collectors/
    ├── base.py           # Collector Protocol
    ├── google_news.py    # Google News RSS (query "Warszawa when:1d")
    ├── tvn_warszawa.py   # TVN Warszawa RSS feed
    ├── um_warszawa.py    # um.warszawa.pl HTML scraper (fragile, may need selector updates)
    ├── reddit.py         # Reddit r/warsaw public JSON API (no key needed)
    ├── wykop.py          # Wykop.pl API v3 (needs WYKOP_KEY + WYKOP_SECRET)
    ├── rss.py            # Universal RSS collector (used for extra feeds)
    └── bluesky.py        # Bluesky (NOT ACTIVE — API requires auth, kept for future use)

frontend/                # React + Vite SPA
├── src/
│   ├── App.jsx
│   ├── App.css
│   ├── hooks/useEvents.js
│   └── components/      # EventCard, CategoryBadge, RelevanceIndicator, SourceLinks
└── dist/                # Built static files, served by FastAPI in production
```

## Running

```bash
# Install
pip install -e .
cd frontend && npm install && npm run build && cd ..

# Server (backend + frontend on port 8000)
python -m miejskie_trendy.api

# CLI only (JSON to stdout, logs to stderr)
python -m miejskie_trendy.main
```

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...     # Required
WYKOP_KEY=...                     # Optional, free from https://dev.wykop.pl/
WYKOP_SECRET=...                  # Optional
```

All other data sources (Google News RSS, TVN Warszawa RSS, um.warszawa.pl, Reddit, Warsaw Insider, Notes From Poland) are free and require no keys.

## Key Conventions

- **Language:** All user-facing text (prompts, event names, descriptions) is in Polish
- **Adding RSS feeds:** Add a tuple `(url, name)` to `EXTRA_RSS_FEEDS` in `main.py`
- **Adding a new collector:** Create a class with `name: str` and `async def collect(self) -> list[RawItem]`, add to collectors list in `main.py`
- **API cache:** In-memory, 15-minute TTL, with asyncio.Lock to prevent concurrent Claude calls. `POST /api/events/refresh` clears cache
- **um.warszawa.pl scraper:** Most fragile component — if HTML structure changes, update selectors in `um_warszawa.py`
- **Date filtering:** Normalizer uses 24h lookback from start of today (UTC), not strict "today only" — handles late-night articles gracefully
- **Claude model:** `claude-sonnet-4-20250514` in `grouper.py`
- **Frontend build:** `frontend/dist/` is served by FastAPI's StaticFiles mount. After frontend changes, run `cd frontend && npm run build`
- **No database:** Everything is in-memory. Each server restart fetches fresh data on first request

## Deployment (Railway)

- **Dockerfile:** Multi-stage build (Node for frontend, Python for backend). Railway auto-detects it.
- **Env vars in Railway dashboard:** `ANTHROPIC_API_KEY` (required), `WYKOP_KEY`, `WYKOP_SECRET` (optional). Railway sets `PORT` automatically.
- **`FRONTEND_DIST`:** Set in Dockerfile to `/app/frontend/dist`. Override if frontend dist is elsewhere.
- **Frontend mount:** Happens at FastAPI startup event, not import time — ensures Docker layer ordering works.
- **Docker build tested:** `docker build -t miejskie-trendy . && docker run -p 8000:8000 -e ANTHROPIC_API_KEY=... miejskie-trendy`
