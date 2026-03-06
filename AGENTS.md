You are a coding agent that develops the simplest, most elegant and principal-engineer level solutions.


1. Upon initialization echo `reading AGENTS.md`
2. Before beginning a task, think about the feature that your task is supporting. Think of the best title (e.g. `feature/sms-2fa` for a 2FA via SMS) or `fix/typo` and save it and what you're about to do to with `{datetime} in `LOG.md`
3. REQUIREMENTS.md is for humans, not agents. You are to keep it up to date with an accurate executive summary of what the purpose of this app is and the requirements for fulfilling it. After completing a task, or being far enough alone some iterative task with the user, reflect on REQUIREMENTS.md , add any missing statements and fix any inaccuracies


## Development Patterns
1. always have info logs for API endpoints that provide info like `[api_endpoint_name] starting {first task}` , `[api_endpoint_name] completed {resultant data}` or `[api_endpoint_name] error: {error}`
2. the following files serve as foundation. sometimes, there there will be multiple of them (e.g. different modules may have their won respective schemas.py )
    - schemas.py - these are pydantic classes used for llm responses . keep them simple and follow the patterns that already exist.
    - models.py - these are the sqlalchemy classes used to store data in our db , which is sqlite locally and postgres while deployed.
    - prompts.py - these are our static prompts for llm responses, etc.
    - agents.py - these are our Pydantic AI agents, used to design our llm workflows and agents. follow the patterns that exist
    - frontend/*
        - React + TypeScript + Vite
        - keep things as simple as possible - e.g. do not use strong types that break the UI when an api endpoint response changes slightly (but do let us know about any discrepancies like this)
        - For landing pages, include Helmet OG tags in component and update preview strategy docs . Think about S.E.O. and social sharing implications, and provide options that balance those goals with minimalism.
3) Keep route handlers thin; move business logic to services/helpers.
4) All LLM outputs must validate against Pydantic schemas.
5) DB schema changes require migrations; avoid runtime `create_all` except local bootstrap mode.
6) API logs must include start/success/error with endpoint name, request_id, duration_ms, and status_code.
7) Never log secrets, tokens, full phone numbers, or raw PII.


