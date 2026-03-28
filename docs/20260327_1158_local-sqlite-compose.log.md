# Local SQLite Compose

- Timestamp: 2026-03-27T11:58:02-1000
- Feature branch name: `feature/local-sqlite-compose`

## Goal

Make local docker compose boot reliably even when `.env` contains remote database credentials that are invalid or unavailable.

## Decisions

- The backend service now defaults `DB_ENGINE_URL` to `sqlite:////data/oahuai.db` inside Compose.
- Remote or non-default databases remain possible through `BACKEND_DB_ENGINE_URL`.
- The frontend container no longer inherits the full backend `.env`.

## Work Completed

- Overrode the backend DB URL in Compose.
- Removed the frontend `env_file` inheritance.
- Updated requirements notes and logs for the new local startup contract.
