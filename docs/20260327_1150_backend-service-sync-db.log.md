# Backend Service Sync DB

- Timestamp: 2026-03-27T11:50:23-1000
- Feature branch name: `feature/backend-service-sync-db`

## Goal

Make the Compose backend service name match the repo vocabulary and ensure the backend container starts with the current Postgres env configuration.

## Decisions

- Renamed the Compose service from `api` to `backend` so operational commands read naturally.
- Kept the browser proxy model from the frontend, but pointed it at `http://backend:8000`.
- Normalized `postgresql+asyncpg://` to `postgresql+psycopg://` inside the sync database bootstrap instead of converting the whole app to async SQLAlchemy.

## Work Completed

- Updated `docker-compose.yml` service naming and proxy target wiring.
- Added `psycopg[binary]` to Python dependencies.
- Added database URL normalization for sync engine startup.
