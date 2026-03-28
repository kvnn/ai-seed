# Backend Package Layout Log

- Timestamp: 2026-03-27T12:54:40-1000
- Feature: `feature/backend-package-layout`
- Git revision baseline: `5c498aa`

## Goal

Make `backend/` the only canonical Python package root by relocating the useful modules that were still sitting under the removed `src/services` tree.

## Decisions

- Keep domain-specific code under `backend/apps/<domain>/...`.
- Keep cross-cutting integrations under `backend/services/...`.
- Do not preserve the old `src/services/auth` layout because `backend/apps/auth` is already the active implementation.

## Work

- Verified the moved modules now live under `backend/apps/brand`, `backend/apps/generation`, `backend/services/firecrawl`, and `backend/services/storage`.
- Normalized moved-module imports from `app.*` to `backend.*`.
- Split brand schemas/prompts into app-local modules so the moved code follows the repo's backend app pattern.
- Documented `backend/` as the canonical package root in requirements and notes.
