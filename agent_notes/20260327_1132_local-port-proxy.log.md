# Local Port Proxy

- Timestamp: 2026-03-27T11:32:04-1000
- Feature branch name: `feature/local-port-proxy`

## Goal

Prevent local Docker startup from failing when a fixed backend host port is already in use.

## Decisions

- Stopped publishing the backend port to the host by default.
- Made the Vite frontend proxy `/api`, `/preview`, and `/health` to the `api` service over the Compose network.
- Kept the frontend host port configurable with `FRONTEND_HOST_PORT`.

## Work Completed

- Updated `docker-compose.yml` to expose the API internally instead of binding `API_HOST_PORT`.
- Updated Vite config to proxy backend traffic.
- Changed the frontend API client default base URL to same-origin.
