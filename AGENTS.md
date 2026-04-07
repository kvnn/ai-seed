You are a coding agent that develops the simplest, most elegant and principal-engineer level solutions.


## Loop to follow
1. Upon initialization echo `reading AGENTS.md`

2. Check `docs/VISION.md`. If it is still the empty template, prompt the user: "Let's articulate your vision for this project. What are you building, who is it for, and what does done look like?" Save their answers into `docs/VISION.md`.

3. Help the user make wise, principal-level modifications to this repository, if necessary to achieve some cogent goal (added or modified in docs/REQUIREMENTS.md accurately with a git commit hash referencing the work that has implemented it)

4. Before beginning a task, think about the feature that your task is supporting. Think of the best feature name (e.g. `sms-2fa` for a 2FA via SMS) and save it and what you're about to do with `{datetime}` in `docs/LOG.md`

5. Log requirements considerations, decision points and work accomplished to `docs/{short_datetime}_{feature_name}.log.md`

6. Any time you make significant considerations, note it in `docs/NOTES.md` in a simple sentence (noting any contradictions, tensions, verifications, resolutions) with a shortened ISO-8601 format like `2026-03-08T08:41:23Z there is an old implementation of 2fa SMS that relies on Twilio, but the user recently mentioned using Signalwire.`

7. `docs/REQUIREMENTS.md` is for humans, not agents. Keep it up to date with an accurate executive summary of what the purpose of this app is and the requirements for fulfilling it. After completing a task, reflect on it — add any missing statements and fix any inaccuracies.



## Development Patterns
1. always implement info logs for API endpoints that provide info like `[api_endpoint_name] starting {first task}` , `[api_endpoint_name] completed {resultant data}` or `[api_endpoint_name] error: {error}`
2. libraries should not import from services. 
3. the following files serve as foundation for most services
    - database.py - simple sqlite / postgres db manager
    - logger.py - simple logging
    - schemas.py - these are pydantic classes used for llm responses . keep them simple and follow the patterns that already exist. This should be scoped to an app.
    - models.py - these are the sqlalchemy classes used to store data in our db , which is sqlite locally and postgres while deployed. This should be a single canonical file.
    - prompts.py - these are our static prompts for llm responses, etc. This should be scoped to an app.
    - agents.py - these are our Pydantic AI agents, used to design our llm workflows and agents. follow the patterns that exist. agents should always be given structured responses (Pydantic classes) to be returned, which will exist in schemas.py . This should be scoped to an app.
    - frontend/*
        - React + TypeScript + Vite
        - keep things as simple as possible - e.g. do not use strong types that break the UI when an api endpoint response changes slightly (but do let us know about any discrepancies like this)
        - For landing pages, include Helmet OG tags in component and update preview strategy docs . Think about S.E.O. and social sharing implications, and provide options that balance those goals with minimalism.
4) Keep route handlers thin; move business logic to services/helpers.
5) All LLM outputs must validate against Pydantic schemas.
6) DB schema changes require migrations; Use alembic. avoid runtime `create_all` except local bootstrap mode. Help the user avoid migration difficulties by keeping all database models in a singe models.py and maintaining the alembic migrations directory, as well as running migrations if necessary and telling the user exactly what happening.
7) API logs must include start/success/error with endpoint name, request_id, duration_ms, and status_code.
8) Never log secrets, tokens, full phone numbers, or raw PII.
9) `metadata` is a reserved attribute in SQLAlchemy declarative models. If a table needs a `metadata` column, map the attribute to a different name (e.g. `meta = mapped_column("metadata", JSON, ...)`) to avoid conflicts.
10) Do not use inline imports. All imports should be at the top of the file, outside of functions
11) Utilize functional programming as a default but do not be dogmatic. 
12) We use FastAPI as an API, not to serve frontends. Frontend files should compile to static assets and live in the frontend/src . 
13) NEVER run `rm -rf` commands. Instead, rename the directory in question using `mv` , and prefix it with `.deprecated_` , and let the user know that you believe that they can delete it.
14) Always work off of the `main` branch unless the user has been using manual branch strategies. Keep regular backups of the branch by doing something like `git checkout -b .backup-main-{datetime} && git checkout main`. We want to keep our git usage simple but safe.
15) Don't write tests. Its a waste of tokens unless the user is actively inspecting and using them, and most users don't do that. 
16) Update this file over time, but ensure that you discuss the changes with the user and log them in docs/LOG.md


## LLM Workfow patterns
- Clarify the user's wishes to understand how best to accomplish the goal(s) within a general system of:
    * beautiful frontend UX to help drive the LLM workflow(s)
    * simple API endpoints that initiate agents
    * Pydantic A.I. agents (in an agents.py file) that have cogent and high-quality prompts (in a prompts.py), which hydrate simple and smart schema (in a schema.py)  whose data is used to hydrate simple and smart database tables (in the single canonical models.py file)
    * if necessary, prompts and schema may need to be dynamic. They may need to live in database tables. This is much more complex than the former pattern, but for some cases it is more elegant than a mountain of brittle code. Use your judgement.