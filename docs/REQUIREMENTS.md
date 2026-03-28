# OahuAI Seed Requirements

Implementation reference: current working tree based on git revision `5c498aa`.

## Executive Summary

OahuAI Seed is a cloneable starter repo for building LLM workflow apps. It packages three years of applied-AI web app patterns into a single repository that non-technical people can clone, configure, and start building from with Claude Code.

The seed supports a three-track build progression — static website, web app, AI workflow app — and is the canonical deployment seed for the OahuAI "Claude Code 101" workshop series. Workshop attendees clone this repo, articulate their project vision in `docs/VISION.md`, and use Claude Code to build and deploy their own app.

Vendor credentials (AWS S3, OpenAI, Firecrawl) are provisioned by the workshop operator to keep the technical barrier low.

## Current Requirements

### Seed landing page
- The public index page must explain what this repo is: a starting point for building LLM workflow apps.
- The landing page must show the three-track build progression (static site, web app, AI workflow app).
- The landing page must surface the included patterns library and what the stack provides (auth, database, storage, frontend, LLM agents, deploy).
- The landing page must include clear "get started" steps: clone, configure, articulate vision, build.
- The landing page must set social preview metadata and use a stable preview image asset for sharing.
- OahuAI branding should be present but easy to find-and-replace for downstream projects.

### Vision workflow
- The repo must include a `docs/VISION.md` template that prompts the user to describe what they're building, who it's for, and what done looks like.
- Claude Code should read `docs/VISION.md` on initialization to ground every conversation in the user's intent.

### Stack and infrastructure
- The frontend must live in the top-level `frontend/` directory because `docker-compose.yml` mounts that path into the Node service.
- The Python package must live in `backend/` and Docker plus import paths must consistently reference `backend`, not `app`.
- Domain-owned backend code must live under `backend/apps/<domain>/...`, while only cross-cutting adapters should live under `backend/services/...`.
- The repository should not retain an active `src/services` Python tree; `backend/` is the only supported package root.
- Optional backend integrations may depend on extra packages, but those imports should fail lazily with clear runtime errors rather than breaking app startup when the integration is unused.
- Local Docker development must not depend on reserving a fixed backend host port if the frontend can proxy to the API container over the Compose network.
- Local Docker should expose the backend service under the Compose name `backend`, and the backend should tolerate async-style Postgres URLs in env by normalizing them for the sync runtime.
- Local Docker should default the backend database to a writable SQLite file in `/data` unless an explicit backend-specific DB override is supplied.
- The frontend container should only receive frontend-specific environment variables, not the backend's secret-bearing `.env` wholesale.

### Authentication and operator console
- Operators must be able to authenticate, bootstrap the first admin on a fresh stack, or register with an invite code.
- The authenticated workshop UI should remain available under a protected route while the public index page remains accessible without sign-in.

### Patterns library
- The `patterns/` directory must contain self-contained architecture pattern docs covering: crawl-cache-generate, LLM agent factory, SSE streaming, storage backend swap, custom domain lifecycle, and async DB patterns.
- Each pattern doc must include problem, solution, code, pitfalls, and an adaptation guide.

### Deployment
- The stack must be deployable to Render (or similar container hosts) with minimal configuration.
- AWS S3 is the default media storage backend for production deployments.
