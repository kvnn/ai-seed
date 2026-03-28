# Pattern: Async Database for FastAPI + SQLAlchemy

## Problem

FastAPI is async. SQLAlchemy supports both sync and async. You need:
- Async sessions for your API endpoints (don't block the event loop)
- Sync sessions for Alembic migrations (which don't support async)
- Connection pooling tuned to your environment (dev vs staging vs prod)
- Monitoring to catch pool exhaustion before it becomes an outage

Naively using sync SQLAlchemy in async FastAPI blocks the entire server on every DB call. Using only async means your migrations break.

## Pattern

Maintain **two engines** (sync + async) against the same database, with environment-aware pool configuration and connection event monitoring.

```
┌─────────────────────────────────────────┐
│              Application                │
├──────────────────┬──────────────────────┤
│   Async Engine   │    Sync Engine       │
│                  │                      │
│   FastAPI        │    Alembic           │
│   endpoints      │    migrations        │
│   background     │    health checks     │
│   tasks          │    scripts           │
│                  │                      │
│   AsyncSession   │    Session           │
│   Local          │    Local             │
├──────────────────┴──────────────────────┤
│          Connection Pool                │
│   (QueuePool for Postgres)              │
│   (NullPool for SQLite)                 │
└─────────────────────────────────────────┘
```

### URL Conversion

Async and sync engines need different URL schemes:

```python
def get_sync_url(url: str) -> str:
    """Convert async DB URL to sync URL."""
    if "asyncpg" in url:
        return url.replace("postgresql+asyncpg://", "postgresql://")
    if "+aiosqlite" in url:
        return url.replace("+aiosqlite", "")
    return url
```

Your config stores the async URL (the primary). The sync URL is derived.

### Environment-Aware Pool Sizing

```python
def get_pool_config(environment: str) -> tuple[int, int, int]:
    """Returns (pool_size, max_overflow, pool_timeout) per environment."""
    configs = {
        "production":  (20, 40, 30),
        "staging":     (10, 20, 30),
        "development": (5, 10, 30),
    }
    return configs.get(environment, configs["development"])
```

**Key decisions:**
- **`pool_size`**: Number of persistent connections. Match roughly to your expected concurrent request count.
- **`max_overflow`**: Extra connections allowed during spikes. These are created and destroyed per-use. Set to 2x `pool_size` for production.
- **`pool_timeout`**: How long to wait for a connection before raising. 30s is generous; reduce to 10s if you'd rather fail fast.

### Dual Engine Setup

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

pool_size, max_overflow, pool_timeout = get_pool_config(settings.environment)

# --- Sync engine (Alembic, health checks, scripts) ---
sync_url = get_sync_url(settings.db_url)

if sync_url.startswith("postgresql"):
    sync_engine = create_engine(
        sync_url,
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args={
            "connect_timeout": 10,
            "application_name": f"myapp-{settings.environment}",
            "options": "-c statement_timeout=30000",  # 30s query timeout
        },
    )
elif sync_url.startswith("sqlite"):
    sync_engine = create_engine(
        sync_url,
        poolclass=NullPool,  # SQLite doesn't benefit from pooling
        connect_args={"check_same_thread": False},
    )

# --- Async engine (FastAPI endpoints) ---
async_url = settings.db_url
if "postgresql://" in async_url and "asyncpg" not in async_url:
    async_url = async_url.replace("postgresql://", "postgresql+asyncpg://")

if async_url.startswith("sqlite"):
    async_engine = create_async_engine(
        async_url,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )
else:
    async_engine = create_async_engine(
        async_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

# --- Session factories ---
SessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)
AsyncSessionLocal = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)
```

**Key decisions:**
- **`pool_pre_ping=True`**: Tests each connection before checkout. Catches stale connections from network blips or DB restarts. Adds ~1ms per query but prevents "connection already closed" errors.
- **`pool_recycle=3600`**: Recycle connections after 1 hour. Prevents issues with firewalls or load balancers that silently drop idle connections.
- **`expire_on_commit=False`**: After commit, SQLAlchemy normally marks all loaded objects as expired (triggering lazy loads on next access). Disabling this prevents "greenlet_spawn has not been called" errors in async code and unexpected queries.
- **`NullPool` for SQLite**: SQLite doesn't handle concurrent connections well. NullPool creates a fresh connection per request and closes it immediately.
- **`statement_timeout=30000`**: Kills runaway queries after 30 seconds. Without this, a bad query can hold a connection forever.
- **`application_name`**: Shows up in `pg_stat_activity`, making it easy to identify which app is holding connections.

### Connection Event Monitoring

Register event listeners on the sync engine for observability:

```python
from sqlalchemy import event

@event.listens_for(sync_engine, "connect")
def on_connect(dbapi_connection, connection_record):
    logger.info("New database connection established")

@event.listens_for(sync_engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """Warn when pool is getting full."""
    current = sync_engine.pool.size()
    threshold = pool_size * 0.8
    if current > threshold:
        logger.warning("High pool usage: %d/%d", current, pool_size + max_overflow)

@event.listens_for(sync_engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """Recycle disconnected connections."""
    if connection_record.info.get("disconnected"):
        logger.info("Recycling disconnected connection")
        return False  # Don't reuse this connection
```

### Session Usage Patterns

#### In FastAPI endpoints (async):

```python
# As a dependency
async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/items")
async def list_items(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Item))
    return result.scalars().all()
```

#### In service classes (async):

```python
class ItemService:
    async def get_item(self, item_id: str) -> dict:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Item).where(Item.id == item_id)
            )
            item = result.scalars().first()
            if not item:
                raise NotFound(f"Item {item_id}")
            return item.to_dict()

    async def create_item(self, data: dict) -> dict:
        async with AsyncSessionLocal() as session:
            item = Item(**data)
            session.add(item)
            await session.commit()
            return item.to_dict()
```

#### In scripts/migrations (sync):

```python
from contextlib import contextmanager

@contextmanager
def get_db():
    """Sync session with retry."""
    max_retries = 3
    for attempt in range(max_retries):
        session = SessionLocal()
        try:
            session.execute(text("SELECT 1"))  # Verify connection
            yield session
            session.commit()
            return
        except (DBAPIError, DisconnectionError) as e:
            session.rollback()
            if attempt >= max_retries - 1:
                raise
            logger.warning("DB retry %d/%d: %s", attempt + 1, max_retries, e)
        finally:
            session.close()
```

### Concurrent Write Safety

For operations that must not race (e.g., creating a project with a unique subdomain), use an async lock:

```python
class ProjectStore:
    _create_lock = asyncio.Lock()

    async def create_project(self, user_id: str, data: dict) -> dict:
        async with self._create_lock:
            async with AsyncSessionLocal() as session:
                project = Project(id=generate_id(), user_id=user_id, **data)
                session.add(project)
                await session.commit()
                return project.to_dict()
```

**When to use this:** Only for operations where a DB unique constraint isn't sufficient (e.g., when the ID is generated in Python and you need to avoid collisions across concurrent requests). For most cases, rely on DB constraints.

### Pool Status Monitoring

Expose pool health for your monitoring stack:

```python
def get_pool_status() -> dict:
    pool = sync_engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow(),
    }

async def check_health() -> dict:
    try:
        # Check async
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        # Check sync
        with get_db() as session:
            session.execute(text("SELECT 1"))
        return {"status": "healthy", "pool": get_pool_status()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e), "pool": get_pool_status()}
```

Wire this into a `/health` endpoint that your load balancer checks.

### SQLite vs PostgreSQL Compatibility

Keep your code database-agnostic where possible:

| Concern | SQLite | PostgreSQL |
|---|---|---|
| Pool class | `NullPool` | `QueuePool` |
| Async driver | `aiosqlite` | `asyncpg` |
| `check_same_thread` | `False` (required) | N/A |
| Connection timeout | N/A | `connect_timeout=10` |
| Query timeout | N/A | `statement_timeout=30000` |
| JSON column | Stored as text | Native JSONB |
| Unique constraint on conflict | Limited `ON CONFLICT` | Full `ON CONFLICT DO UPDATE` |

**Tip:** Use SQLite for local development and tests, PostgreSQL for staging/production. The dual-engine setup makes this seamless — your config just changes the `DB_URL`.

## Pitfalls

1. **Blocking the event loop**: Using `SessionLocal` (sync) in an async endpoint blocks all concurrent requests. Always use `AsyncSessionLocal` in async contexts.

2. **`expire_on_commit=True` (the default)**: After commit, accessing any attribute triggers a lazy load. In async code, this raises `MissingGreenlet`. Always set `expire_on_commit=False`.

3. **No `pool_pre_ping`**: After a DB restart or network blip, pooled connections are dead but the pool doesn't know. First request after recovery fails. `pool_pre_ping=True` prevents this.

4. **No `pool_recycle`**: Long-lived connections get killed by firewalls/load balancers (AWS RDS proxy has a 24h limit). Set `pool_recycle` to recycle before that threshold.

5. **Over-sized pools**: A pool of 50 connections against a PostgreSQL instance with `max_connections=100` leaves no room for migrations, monitoring, or other services. Size conservatively.

6. **No statement timeout**: A single runaway query (accidental full table scan, missing index) can hold a connection indefinitely, starving the pool. Set `statement_timeout`.

7. **Using `create_all()` in production**: Fine for bootstrapping a dev SQLite DB. In production, use Alembic migrations so schema changes are versioned and reversible.

## When NOT to Use This Pattern

- **Sync-only framework**: If you're using Flask or Django (without async), you only need the sync engine. Skip the async half.
- **Serverless (Lambda)**: Connection pooling across invocations requires an external pool (RDS Proxy, PgBouncer). In-process pooling is useless when the process dies after each request.
- **Simple scripts**: A one-off data migration doesn't need pool monitoring or dual engines. Use `create_engine()` directly.

## Adapting This Pattern

| If you're using... | Replace... |
|---|---|
| Django ORM | The SQLAlchemy setup. Django has its own connection pooling (`CONN_MAX_AGE`) and async support (`aconnect`/`adatabase_sync_to_async`). |
| Tortoise ORM | Both engines. Tortoise is async-native and handles pooling internally. |
| Raw `asyncpg` | The ORM layer. Keep the pool sizing and monitoring concepts. |
| PgBouncer/RDS Proxy | Reduce your in-app pool size (the proxy handles pooling). Set `pool_size=2, max_overflow=3` and let the proxy manage the rest. |
