# Workshop Seed Frontend

- Timestamp: 2026-03-26T11:03:06-1000
- Feature branch name: `feature/workshop-seed-frontend`
- Base revision: `5c498aa`

## Goal

Materialize `reference/frontend` into the actual top-level `frontend/` app expected by `docker-compose.yml`, then adapt it to the workshop product and the current auth/run backend.

## Decisions

- Reused the reference frontend as the filesystem base, but replaced the crawlbuild-specific screens with a smaller workshop-specific UI.
- Kept the implementation aligned to the existing `/api/auth` and `/api/runs` endpoints instead of inventing a larger missing API surface.
- Fixed the API container path assumptions in `docker-compose.yml` so the current repository layout is runnable.
- Added in-component social preview metadata for the landing page using a small local component instead of expanding the dependency surface.

## Work Completed

- Created the real `frontend/` app in the repository root.
- Implemented auth restore, login, register, and bootstrap admin flows.
- Implemented workshop landing, run navigator, run workspace, preview iframe, and stage actions.
- Updated requirements and notes documents to reflect the workshop product and the new frontend.
