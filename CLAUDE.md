# Miejskie Trendy

Warsaw city events tracker — collects news articles and social media posts about events affecting Warsaw residents, groups them using Claude AI, and displays them in a dark glass-morphism web UI.

## Architecture

```
[Collectors] → [Normalizer] → [Claude Sonnet Grouper] → [SQLite DB] ← [FastAPI] → [React Frontend]
                                                              ↑
                                                    [Background Scheduler]
```

**Pipeline:** Async collectors gather raw articles in parallel → normalizer deduplicates and filters by time → Claude Sonnet selects relevant city events, groups related articles, extracts locations → results stored in SQLite. Background scheduler runs updates periodically. Frontend polls API every 30s.

**Key design decision:** The Claude prompt in `prompt.py` is the primary configuration for what counts as a "city event." Changing the scope means editing the prompt text, not the code. Two prompts exist: `SYSTEM_PROMPT` (fresh mode) and `MERGE_PROMPT` (incremental updates with existing events).

## Project Structure

```
src/miejskie_trendy/
├── main.py              # CLI entry point, orchestrates pipeline, run() returns list[dict]
├── api.py               # FastAPI server, serves /api/events + settings + logs + static frontend
├── config.py            # Shared constants: EXTRA_RSS_FEEDS, MODEL, strip_markdown_fences()
├── models.py            # RawItem, Source, Event dataclasses
├── db.py                # SQLite: events, sources, settings, logs tables
├── normalizer.py        # URL dedup, date filtering (24h lookback, 72h on first run)
├── grouper.py           # Claude Sonnet API call, parses JSON response into Events
├── updater.py           # Full update cycle: collect → match → merge via Claude → save to DB
├── scheduler.py         # Background asyncio task, reads interval/enabled from DB settings
├── prompt.py            # System prompt + merge prompt + message builders (MOST IMPORTANT for tuning)
└── collectors/
    ├── base.py           # Collector Protocol
    ├── google_news.py    # Google News RSS (per-day queries to bypass 100-result limit)
    ├── tvn_warszawa.py   # TVN Warszawa RSS feed
    ├── um_warszawa.py    # um.warszawa.pl HTML scraper (fragile, may need selector updates)
    ├── reddit.py         # Reddit r/warsaw public JSON API (no key needed)
    ├── wykop.py          # Wykop.pl API v3 (needs WYKOP_KEY + WYKOP_SECRET, graceful skip if missing)
    ├── rss.py            # Universal RSS collector (used for extra feeds in EXTRA_RSS_FEEDS)
    └── bluesky.py        # Bluesky (NOT ACTIVE — API requires auth, kept for future use)

frontend/                # React + Vite SPA, dark glass-morphism UI
├── src/
│   ├── App.jsx / App.css
│   ├── hooks/useEvents.js    # Polls /api/events, detects new events vs new sources
│   ├── utils/formatDate.js   # Shared date formatting (formatShortDate, formatFullDate, formatLogDate)
│   └── components/
│       ├── EventCard.jsx     # Card with category badge, relevance dots, location, time range
│       ├── EventList.jsx     # React.memo wrapped list
│       ├── CategoryBadge.jsx # Colored translucent pill per category
│       ├── RelevanceIndicator.jsx
│       ├── SourceLinks.jsx   # Expandable sources with "N nowych" badge, Sparkles icon on new
│       ├── ActivityChart.jsx # Variable-width histogram (6h bins, auto-subdivide dense ones, useMemo)
│       ├── TimeRange.jsx     # Earliest–latest source date span
│       ├── SettingsDialog.jsx # Refresh interval, on/off, API keys
│       └── LogsDialog.jsx    # Scrollable activity log from DB
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
ANTHROPIC_API_KEY=sk-ant-...         # Required (or set via Settings UI)
WYKOP_KEY=...                         # Optional, free from https://dev.wykop.pl/
WYKOP_SECRET=...                      # Optional
UPDATE_INTERVAL_MINUTES=60            # Default scheduler interval
DATABASE_PATH=data/events.db          # SQLite path
```

API keys can also be set via the Settings dialog in the UI (stored in SQLite, override env vars).

## API Endpoints

- `GET /api/events` — read active events from DB (instant, no pipeline)
- `POST /api/events/refresh` — trigger immediate update cycle (60s cooldown, returns 429 if too frequent)
- `POST /api/events/rebuild` — clear DB and do fresh 3-day collection (shares 60s cooldown with refresh)
- `GET /api/settings` — get settings (keys masked)
- `PUT /api/settings` — save settings, notify scheduler
- `GET /api/logs` — get activity logs (last 200 entries)

## Key Conventions

- **Language:** All user-facing text (prompts, event names, descriptions) is in Polish
- **Adding RSS feeds:** Add a tuple `(url, name)` to `EXTRA_RSS_FEEDS` in `config.py`
- **Adding a new collector:** Create a class with `name: str` and `async def collect(self) -> list[RawItem]`, add to collectors list in `updater.py`
- **um.warszawa.pl scraper:** Most fragile component — if HTML structure changes, update selectors
- **Date filtering:** 24h lookback normally, 72h on first run (empty DB). Google News uses per-day queries to bypass 100-result limit.
- **Merge logic:** Hybrid — URL overlap pre-matching + Claude merge prompt. Merge mode does NOT deactivate events omitted by Claude (prevents data loss from token limits/hallucination). Fresh mode deactivates all prior events. Claude API calls have a 120s timeout.
- **Claude model:** `claude-sonnet-4-20250514` in `config.py` (shared constant)
- **Frontend:** Dark glass-morphism theme, Lucide icons, auto-polls every 30s
- **Update indicators:** "Nowy temat" badge (fades 30s) for new events, "N nowych" golden Sparkles badge for new sources (persists until next scheduler refresh)
- **Activity chart:** Fixed 2px/hour scale across all events. 6h bins, auto-subdivide dense bins (5+ articles → 3h, 7+ → 2h, 10+ → 1h). Axis labels at 00/12h, dates on separate row.
- **Settings:** Stored in SQLite `settings` table. Scheduler re-reads on change via asyncio.Event.
- **Logs:** Stored in SQLite `logs` table (max 500 entries). Updater logs collector results, normalization, Claude calls, found events.

## Deployment (Railway)

- **Live URL:** https://miejskie-trendy-production.up.railway.app
- **GitHub:** https://github.com/pafcioezhtml/miejskie-trendy
- **Railway project:** `brilliant-peace`, service `miejskie-trendy`, volume at `/app/data`
- **Dockerfile:** Multi-stage build (Node for frontend, Python for backend)
- **Persistent volume:** SQLite DB at `/app/data/events.db` — survives redeploy
- **Frontend mount:** Happens at FastAPI lifespan startup, `FRONTEND_DIST=/app/frontend/dist`
- **Railway sets `PORT` automatically.** `api.py` reads from env.

### Railway CLI commands

```bash
railway up -s miejskie-trendy --detach          # Deploy
railway variables set KEY=value -s miejskie-trendy  # Set env vars
railway logs -s miejskie-trendy                 # View logs
railway domain -s miejskie-trendy               # Public domain
```
