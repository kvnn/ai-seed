# Backend Index Surface

- Timestamp: 2026-03-27T09:42:16-1000
- Feature branch name: `feature/backend-index-surface`
- Base revision reference: `5c498aa`

## Goal

Make the `app` to `backend` rename coherent and expose a simple frontend index page that proves the frontend can fetch live data from the backend.

## Decisions

- Added a small public system endpoint rather than abusing shell execution from the browser.
- Kept the authenticated workshop UI intact by moving it under `/studio`.
- Rendered the backend root snapshot in a styled terminal-like block so the index page stays simple and obviously data-driven.

## Work Completed

- Updated Docker and Compose commands to use `backend.main:app`.
- Repointed Python imports and tests from `app.*` to `backend.*`.
- Restored the missing `InviteCode` and `Run` models required by the existing auth and run services.
- Added `/api/system/backend-root`.
- Added a public frontend index page that renders the backend root listing.
