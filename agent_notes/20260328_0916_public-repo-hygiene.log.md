# Public Repo Hygiene Log

- Timestamp: 2026-03-28T09:16:11-1000
- Feature: `feature/public-repo-hygiene`
- Git revision baseline: `e5607bf`

## Goal

Review the current working tree for anything that should not be pushed to a public repository.

## Findings

- `.env` contains real local runtime secrets and must remain private.
- `data/` is ignored and likely contains local database state that should not be published.
- `.claude/settings.local.json` is already ignored by the global gitignore and contains local tooling permissions, not app runtime secrets.
- The untracked `reference/` directory appears to contain a copied frontend reference plus `node_modules` and built assets; it is not obviously secret, but it is likely noise unless intentionally published.
- `backend/config.py` currently allows JWT signing to fall back to `APP_PASSWORD` and then `"change-me"`, which is acceptable for local bootstrap but weak for a public starter.

## Recommendation

- Keep `.env` and `data/` private.
- Add a redacted `.env.example` before pushing publicly.
- Tighten the JWT secret requirement before treating the repo as production-ready.
- Decide intentionally whether `reference/` should exist in the public repo at all.
