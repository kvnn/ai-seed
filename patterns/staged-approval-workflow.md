# Pattern: Staged Approval Workflow for LLM Pipelines

## Problem

Your LLM pipeline has multiple stages (research, analysis, generation, etc.) where each stage's output feeds the next. Running the full pipeline in one shot is risky: if the final output is wrong, you've burned tokens on every stage, and you can't tell which stage went wrong. Users need to review intermediate artifacts and course-correct before committing to the next expensive step.

## Pattern

Model the pipeline as a **state machine** where each stage produces an artifact, stores it on the run record, and waits for approval before advancing. Failed stages can be retried without re-running earlier stages.

```
┌───────┐   create   ┌──────────┐  approve  ┌──────────┐  approve  ┌──────────┐
│ DRAFT │───────────>│ STAGE 1  │─────────>│ STAGE 2  │─────────>│ STAGE 3  │
└───────┘            │ building │          │ building │          │ building │
                     └────┬─────┘          └────┬─────┘          └────┬─────┘
                          │                     │                     │
                        fail                  fail                  fail
                          │                     │                     │
                          ▼                     ▼                     ▼
                     ┌──────────┐          ┌──────────┐          ┌──────────┐
                     │  FAILED  │          │  FAILED  │          │  FAILED  │
                     │ (retry)  │          │ (retry)  │          │ (retry)  │
                     └──────────┘          └──────────┘          └──────────┘

After final stage approved:
┌──────────┐  publish  ┌───────────┐
│ APPROVED │─────────>│ PUBLISHED │
└──────────┘           └───────────┘
```

### The State Model

```python
from enum import StrEnum

class RunStatus(StrEnum):
    DRAFT = "draft"
    BUILDING = "building"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    FAILED = "failed"

class RunStage(StrEnum):
    """Ordered stages of the pipeline."""
    RESEARCH = "research"
    ANALYSIS = "analysis"
    GENERATION = "generation"

STAGE_ORDER = list(RunStage)
```

**Key decisions:**
- **`StrEnum`** for database-friendly string values. No integer mapping to maintain.
- **Separate status and stage**. Status is "what state is this run in" (building, failed, review). Stage is "which step of the pipeline." A run can be `FAILED` at stage `ANALYSIS` — you need both to know what happened and where.
- **Stage order is a list**, not implicit. This makes it trivial to find the next stage: `STAGE_ORDER[STAGE_ORDER.index(current) + 1]`.

### The Run Record

Store stage artifacts as JSON columns on a single record. Each stage writes to its own column.

```python
from sqlalchemy import JSON, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_by: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # User inputs
    brief: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stage artifacts (JSON blobs, populated as stages complete)
    research_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    analysis_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generation_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Error tracking
    failed_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Audit trail
    approval_history: Mapped[list[dict]] = mapped_column(JSON, default=list)
```

**Key decisions:**
- **One record per run**, not one record per stage. This makes it trivial to load the full run state in one query. Stage artifacts are JSON columns — flexible and migration-friendly.
- **`failed_stage` + `last_error`** — When a run fails, you know exactly which stage failed and why. This powers the retry UI.
- **`approval_history`** — Append-only list of `{stage, action, notes, timestamp}` dicts. This is your audit trail for "who approved what and when."

### The Service

The service has three core operations: **create**, **approve**, and **retry**.

```python
class RunService:
    def __init__(self, db, research_svc, analysis_svc, generation_svc):
        self._db = db
        self._builders = {
            RunStage.RESEARCH: research_svc.build,
            RunStage.ANALYSIS: analysis_svc.build,
            RunStage.GENERATION: generation_svc.build,
        }

    async def create(self, brief: str, source_url: str | None, user_id: str) -> Run:
        run = Run(
            id=generate_short_id(),
            status=RunStatus.BUILDING,
            created_by=user_id,
            brief=brief,
            source_url=source_url,
        )
        await self._db.save(run)

        # Build first stage immediately
        await self._build_stage(run, STAGE_ORDER[0])
        return run

    async def approve(self, run_id: str, notes: str | None = None) -> Run:
        run = await self._db.get(run_id)

        current_stage = self._current_stage(run)
        self._append_approval(run, current_stage, "approved", notes)

        next_idx = STAGE_ORDER.index(current_stage) + 1
        if next_idx < len(STAGE_ORDER):
            # More stages — build the next one
            await self._build_stage(run, STAGE_ORDER[next_idx])
        else:
            # All stages complete
            run.status = RunStatus.APPROVED

        await self._db.save(run)
        return run

    async def retry(self, run_id: str) -> Run:
        run = await self._db.get(run_id)
        if run.status != RunStatus.FAILED:
            raise ValueError("Can only retry failed runs")

        stage = RunStage(run.failed_stage)
        run.status = RunStatus.BUILDING
        run.failed_stage = None
        run.last_error = None
        await self._db.save(run)

        await self._build_stage(run, stage)
        return run
```

### Building a Stage

Each stage builder receives the run record (with all prior artifacts) and returns a payload dict.

```python
    async def _build_stage(self, run: Run, stage: RunStage) -> None:
        run.status = RunStatus.BUILDING
        await self._db.save(run)

        try:
            builder = self._builders[stage]
            payload = await builder(run)

            # Store artifact on the run
            setattr(run, f"{stage.value}_payload", payload)
            run.status = RunStatus.REVIEW
            await self._db.save(run)

        except Exception as e:
            run.status = RunStatus.FAILED
            run.failed_stage = stage.value
            run.last_error = str(e)
            await self._db.save(run)
            raise

    def _current_stage(self, run: Run) -> RunStage:
        """Determine current stage by which payloads are populated."""
        for stage in reversed(STAGE_ORDER):
            if getattr(run, f"{stage.value}_payload") is not None:
                return stage
        return STAGE_ORDER[0]

    def _append_approval(self, run: Run, stage: RunStage, action: str, notes: str | None):
        entry = {
            "stage": stage.value,
            "action": action,
            "notes": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        run.approval_history = [*run.approval_history, entry]
```

**Key decisions:**
- **`setattr` with stage name** — `research_payload`, `analysis_payload`, etc. follow a naming convention. This avoids a switch statement for each stage.
- **Status transitions are explicit** — `BUILDING` on entry, `REVIEW` on success, `FAILED` on error. No ambiguous intermediate states.
- **Prior artifacts are accessible** — The generation builder can read `run.research_payload` and `run.analysis_payload` to use earlier outputs as context.
- **Approval history is append-only** — `[*existing, new_entry]` creates a new list. Never mutate JSON columns in place (SQLAlchemy may not detect the change).

### The API Layer

Thin endpoints that delegate to the service.

```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/runs")

@router.post("")
async def create_run(req: RunCreateRequest, user=Depends(get_current_user)):
    run = await run_service.create(req.brief, req.source_url, user.id)
    return to_response(run)

@router.post("/{run_id}/approve")
async def approve_run(run_id: str, req: ApprovalRequest, user=Depends(get_current_user)):
    run = await run_service.approve(run_id, req.notes)
    return to_response(run)

@router.post("/{run_id}/retry")
async def retry_run(run_id: str, user=Depends(get_current_user)):
    run = await run_service.retry(run_id)
    return to_response(run)
```

### Determining Available Actions

The frontend needs to know what the user can do next. Derive this from state.

```python
def next_actions(run: Run) -> list[str]:
    match run.status:
        case RunStatus.REVIEW:
            return ["approve"]
        case RunStatus.FAILED:
            return ["retry"]
        case RunStatus.APPROVED:
            return ["publish"]
        case RunStatus.PUBLISHED:
            return []
        case _:
            return []  # BUILDING / DRAFT — wait
```

Include `next_actions` in every API response so the frontend can render the right buttons without duplicating state logic.

## Pitfalls

1. **Running all stages without approval gates**: If stage 2 depends on stage 1 being correct, skipping review means errors compound. Each approval gate is a checkpoint.

2. **Storing artifacts in separate tables**: Joining 3+ tables to reconstruct a run's state is slow and error-prone. JSON columns on one record are simpler for pipeline artifacts.

3. **No `failed_stage` tracking**: If you only store `status=failed`, the user can't tell which stage failed. They have to re-run everything from scratch instead of retrying just the broken stage.

4. **Mutating JSON columns in place**: `run.approval_history.append(entry)` doesn't trigger SQLAlchemy's change detection. Always assign a new list: `run.approval_history = [*run.approval_history, entry]`.

5. **Duplicating state logic in frontend**: If the frontend independently decides what buttons to show based on status, it will drift from the backend. Return `next_actions` from the API.

6. **No audit trail**: Without `approval_history`, you can't answer "who approved the research step?" Append-only history is cheap and invaluable for debugging.

## When NOT to Use This Pattern

- **Fully automated pipelines**: If no human reviews intermediate outputs, skip the approval gates and run stages sequentially. You still want the error tracking and retry logic.
- **Single-stage tasks**: If there's only one LLM call, the state machine adds overhead. Use a simple request/response.
- **Real-time streaming**: If the user watches generation happen live (SSE), the approval model doesn't fit. Combine this pattern with [SSE Streaming](sse-streaming-llm.md) by streaming within a stage, then pausing for approval between stages.

## Adapting This Pattern

| If you need... | Change... |
|---|---|
| More stages | Add entries to `STAGE_ORDER` and add `{stage}_payload` columns. The service logic doesn't change. |
| Parallel stages | Replace sequential `_build_stage` with `asyncio.gather`. Both stages write to their own payload columns. Approve when all complete. |
| Conditional stages | Add a `_should_run(run, stage) -> bool` method. Skip stages whose preconditions aren't met. |
| Rollback on failure | Add a `_rollback_stage(run, stage)` that nullifies the payload and resets status. |
| Per-stage permissions | Check user role in `approve()` against the current stage. Different stages can require different approvers. |
