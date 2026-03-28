# OahuAI Seed

A starting point for building simple, reliable A.I. web applications using [Claude Code](https://claude.ai/claude-code).

You don't need to be a developer. Clone this repo, open Claude Code, describe what you want to build, and start shipping.

## What's inside

**Frontend** — React + TypeScript + Vite with a clean, warm design system.

**Backend** — FastAPI with session auth, admin bootstrap, and invite codes.

**Database** — SQLAlchemy models. SQLite locally, Postgres in production.

**Storage** — Swappable file storage. Local filesystem for dev, S3 for production.

**LLM agents** — Pydantic AI patterns with structured output and cost tracking.

**Patterns library** — Six battle-tested architecture docs in `patterns/` that Claude Code can read and implement for your context:

| Pattern | What it solves |
|---|---|
| Crawl-Cache-Generate | Scrape sites, cache results, feed content to LLMs |
| LLM Agent Factory | Structured LLM output via Pydantic schemas |
| SSE Streaming | Real-time progress during long AI generations |
| Storage Backend Swap | Local-to-S3 without code changes |
| Custom Domain Lifecycle | DNS validation and CDN provisioning |
| Async DB Patterns | Dual sync/async SQLAlchemy with pool tuning |

## Get started

```bash
# 1. Clone
git clone https://github.com/oahuai/seed.git my-project
cd my-project

# 2. Configure
cp .env.example .env
# Add your API keys: OPENAI_API_KEY, AWS credentials, etc.

# 3. Open Claude Code and describe your vision
claude

# 4. Run locally
docker compose up
```

When you open Claude Code, it will ask you to articulate your project vision — what you're building, who it's for, and what "done" looks like. Your answers get saved to `docs/VISION.md` and keep every future conversation grounded in your intent.

## Build progression

The repo supports three levels of complexity. Start simple, add layers when you need them.

1. **Static Website** — Ship a clean, live site before adding any complexity.
2. **Web App** — Add forms, backend logic, and data storage.
3. **A.I. Workflow App** — Layer in LLM agents that interpret, generate, and act on user input.

## Project structure

```
backend/
  apps/           # Domain modules (auth, runs, system, ...)
  services/       # Cross-cutting adapters (storage, external APIs)
  models.py       # Single canonical SQLAlchemy models file
  main.py         # FastAPI application
frontend/
  src/            # React + TypeScript + Vite
patterns/         # Architecture pattern docs for Claude Code
docs/
  VISION.md       # Your project vision (fill this in first)
  REQUIREMENTS.md # Living requirements doc
  LOG.md          # One-line task log for future agents
  NOTES.md        # Short timestamped decisions and tensions
```

## Deploy

The stack is containerized and ready for [Render](https://render.com), Railway, or any container host. AWS S3 handles media storage in production.

## Branding

This repo ships as "OahuAI Seed". To make it yours, search and replace `OahuAI` (16 occurrences across the codebase) with your own name.

---

Built by [OahuAI](https://oahu.ai) from three years of applied-AI web app development.
