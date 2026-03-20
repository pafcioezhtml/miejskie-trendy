# Miejskie Trendy

Real-time Warsaw city events tracker. Aggregates news and social media, uses Claude AI to identify and group events that impact residents' daily life.

## What it does

- Collects articles from 7 sources (Google News, TVN Warszawa, um.warszawa.pl, Reddit, Wykop, Warsaw Insider, Notes From Poland)
- Claude Sonnet filters out national politics/noise, keeps only events with real city impact
- Groups related articles, extracts location and relevance
- Background scheduler updates every hour (configurable)
- Dark glass-morphism UI with activity histograms and live update indicators

## Quick start

```bash
pip install -e .
cd frontend && npm install && npm run build && cd ..

# Set your Anthropic key
export ANTHROPIC_API_KEY=sk-ant-...

# Run
python -m miejskie_trendy.api
# Open http://localhost:8000
```

## Docker

```bash
docker build -t miejskie-trendy .
docker run -p 8000:8000 -e ANTHROPIC_API_KEY=... miejskie-trendy
```

## Deploy

Deployed on [Railway](https://railway.com) with persistent SQLite volume. Push to `main` triggers auto-deploy.

```bash
railway up -s miejskie-trendy --detach
```

## Tech stack

Python (FastAPI, aiohttp, feedparser, BeautifulSoup, Anthropic SDK) + React (Vite, Lucide icons) + SQLite
