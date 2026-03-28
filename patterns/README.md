# Reusable Patterns

Proven patterns extracted from production use in crawlbuild. Each document is self-contained: problem, solution, code, pitfalls, and adaptation guide.

These are **architecture patterns, not libraries**. They give you the judgment behind the code so you can build the right implementation for your context.

## Patterns

| Pattern | What It Solves |
|---|---|
| [Crawl-Cache-Generate](crawl-cache-generate.md) | Scraping external sites, caching results, and feeding content to LLMs with deduplication and truncation |
| [LLM Agent Factory](llm-agent-factory.md) | Structured LLM output via Pydantic schemas, agent factory functions, and per-call cost tracking |
| [SSE Streaming for LLM](sse-streaming-llm.md) | Real-time progress feedback during long LLM generations using Server-Sent Events with async queues |
| [Storage Backend Swap](storage-backend-swap.md) | Abstract file storage interface that swaps between local filesystem and S3 without code changes |
| [Custom Domain Lifecycle](custom-domain-lifecycle.md) | DNS validation, CDN tenant provisioning, and phase state machine for customer "bring your own domain" |
| [Async DB Patterns](async-db-patterns.md) | Dual sync/async SQLAlchemy engines, environment-aware pool tuning, and connection monitoring for FastAPI |

## How to Use These

**For an agent building a new project:** Point the agent at the relevant pattern doc. It contains enough context to implement the pattern without inheriting project-specific decisions.

**For a human developer:** Read the "Problem" and "Pitfalls" sections first. If the problem matches yours, the pattern saves you from the mistakes we already made.

**For adapting:** Each doc ends with an "Adapting This Pattern" table showing how to swap components (e.g., Playwright instead of Firecrawl, Django instead of FastAPI).

## What These Are Not

- Not libraries (no `pip install`)
- Not tied to specific providers (CloudFront, Firecrawl, OpenAI are examples, not requirements)
- Not exhaustive (they cover the patterns that proved most reusable from this project)
