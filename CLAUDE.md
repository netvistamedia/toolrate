# ToolRate — Developer Guide

## What is this

ToolRate is a reliability oracle for AI agents. It rates 600+ tools/APIs so agents pick the right one from the start. Live at https://toolrate.ai.

## Stack

- **Backend**: Python 3.12 + FastAPI (async)
- **Database**: PostgreSQL 16 (via SQLAlchemy 2.0 async + asyncpg)
- **Cache**: Redis 7 (via redis-py async)
- **Migrations**: Alembic (async)
- **Server**: Hetzner Cloud (178.104.171.216), Docker Compose, Caddy for TLS
- **SDKs**: Python (PyPI) + TypeScript (npm), both named `toolrate` (renamed from `nemoflow` 2026-04-12; `nemoflow` on PyPI is deleted)

## Common commands

```bash
# Run tests (from project root, uses SQLite)
source .venv/bin/activate
python -m pytest tests/ -v

# Deploy to production (pushes to GitHub, pulls on server, rebuilds)
./deploy.sh

# Create API key on server
ssh nemoflow@178.104.171.216 "cd ~/nemoflow && docker compose exec app python -m app.cli create-key --tier pro"

# Run seed data
ssh nemoflow@178.104.171.216 "cd ~/nemoflow && docker compose exec app python -m app.seed"

# Import LLM assessments
ssh nemoflow@178.104.171.216 "cd ~/nemoflow && docker compose exec app python -m app.import_assessments"

# View logs
ssh nemoflow@178.104.171.216 "cd ~/nemoflow && docker compose logs app --tail 50"

# Create new migration
source .venv/bin/activate
alembic revision -m "description"
# Then manually write upgrade/downgrade in the generated file
```

## API endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | /v1/auth/register | No | Self-serve API key signup |
| POST | /v1/assess | Yes | Get tool reliability score |
| POST | /v1/report | Yes | Report execution result |
| GET | /v1/discover/hidden-gems | Yes | Tools with high fallback success |
| GET | /v1/discover/fallback-chain | Yes | Best alternatives when tool fails |
| GET | /v1/tools | Yes | Search/browse tools (filter by category, search by name) |
| GET | /v1/tools/categories | Yes | List all tool categories with counts |
| POST | /v1/webhooks | Yes | Register a score change webhook |
| GET | /v1/webhooks | Yes | List your webhooks |
| DELETE | /v1/webhooks/{id} | Yes | Delete a webhook |
| GET | /v1/stats | Yes | Platform metrics |
| GET | /v1/stats/me | Yes | Personal usage stats |
| GET | /health | No | Health check |

Auth = `X-Api-Key` header required.

## Project structure

```
app/
  main.py              — FastAPI app, lifespan, landing page, middleware
  config.py            — Pydantic BaseSettings (env: NEMO_*)
  dependencies.py      — DI: db session, redis, API key auth
  cli.py               — CLI for key creation
  seed.py              — Seed DB with popular tools
  import_assessments.py — Import LLM assessment JSON files
  api/v1/
    assess.py          — POST /v1/assess
    report.py          — POST /v1/report
    discover.py        — GET /v1/discover/*
    stats.py           — GET /v1/stats*
    auth.py            — POST /v1/auth/register
  models/              — SQLAlchemy models (tool, report, api_key, etc.)
  schemas/             — Pydantic request/response schemas
  services/
    scoring.py         — Core scoring algorithm (Bayesian + recency)
    cache.py           — Redis cache operations
    report_ingest.py   — Process incoming reports
    rate_limiter.py    — Redis-based rate limiting
    discovery.py       — Hidden gems + fallback chain analytics
  core/
    security.py        — API key generation, hashing
    exceptions.py      — Custom HTTP exceptions
sdks/
  python/              — PyPI package "toolrate"
  typescript/          — npm package "toolrate"
```

## Scoring algorithm

1. Recency-weighted average (half-life 3.5 days, ~70% weight on last 7 days)
2. Bayesian smoothing (prior alpha=5, beta=1, new tools start at ~83%)
3. Confidence based on effective sample size
4. Failure risk with 24h trend penalty
5. Error category aggregation for pitfalls

## Key design decisions

- No Docker locally — tests use SQLite via aiosqlite
- Models use `Integer` PK (not BigInteger) for SQLite test compat; migration uses BigInteger
- Migration uses `sa.JSON` not `JSONB` for same reason
- Scoring handles timezone-naive datetimes (SQLite strips tzinfo)
- Rate limiting: daily counter per API key + 60/min per IP burst limit
- Registration: email hashed, stored as tag in data_pool field for dedup
