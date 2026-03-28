# Pattern: Crawl-Cache-Generate Pipeline

## Problem

You need to scrape external websites, extract their content, and feed that content into an LLM to produce a derived artifact (a summary, a new site, structured data, etc.). Naive implementations re-scrape on every request, blow past token limits with raw HTML, and couple the crawl step to the generation step so tightly that changing either is painful.

## Pattern

Separate the pipeline into three independent stages connected by a cache layer:

```
┌─────────┐      ┌─────────┐      ┌──────────┐
│  CRAWL  │─────>│  CACHE   │─────>│ GENERATE │
│         │      │          │      │          │
│ Scrape  │      │ Per-user │      │ Truncate │
│ URLs    │      │ dedup    │      │ Compose  │
│ Extract │      │ store    │      │ Validate │
└─────────┘      └─────────┘      └──────────┘
```

### Stage 1: Crawl

Wrap your crawl provider (Firecrawl, Playwright, requests+BeautifulSoup, etc.) behind an async service class.

```python
class CrawlService:
    """Wraps a sync crawl SDK for use in async FastAPI."""

    def __init__(self, api_key: str):
        self._client = SomeCrawlSDK(api_key=api_key)

    async def scrape(self, url: str, formats: list[str] | None = None) -> dict:
        """Async bridge: run sync SDK in a thread."""
        return await asyncio.to_thread(self._scrape_sync, url, formats)

    def _scrape_sync(self, url: str, formats: list[str] | None = None) -> dict:
        logger.info("[crawl] scrape url=%s", url)
        try:
            result = self._client.scrape(url, **({"formats": formats} if formats else {}))
            logger.info("[crawl] scrape ok url=%s size=%d", url, len(str(result)))
            return result
        except Exception as e:
            logger.exception("[crawl] scrape failed url=%s error=%s", url, e)
            raise
```

**Key decisions:**
- **`asyncio.to_thread`** bridges sync-only SDKs into your async stack without blocking the event loop. This is the single most important detail — without it, one slow scrape blocks all other requests.
- **Structured logging** on every call: start, success (with size), failure (with error). You'll need this when debugging "why did generation produce garbage" — the answer is usually "the scrape returned something unexpected."
- **Summarize response payloads** in logs (truncated to ~800 chars) so you can diagnose without drowning in noise.

### Stage 2: Cache (Per-User Deduplication)

Store scrape results keyed by `(user_id, url)`, not by project or session.

```python
# In your data store
async def get_scrape(self, user_id: str, url: str) -> dict | None:
    """Return cached scrape payload, or None."""
    async with AsyncSessionLocal() as session:
        row = await session.execute(
            select(Scrape).where(Scrape.user_id == user_id, Scrape.url == url)
        )
        scrape = row.scalars().first()
        return scrape.payload if scrape else None

async def set_scrape(self, user_id: str, url: str, payload: Any) -> None:
    """Upsert scrape result."""
    async with AsyncSessionLocal() as session:
        row = await session.execute(
            select(Scrape).where(Scrape.user_id == user_id, Scrape.url == url)
        )
        existing = row.scalars().first()
        now = datetime.now(timezone.utc)

        if existing:
            existing.payload = payload
            existing.scraped_at = now
        else:
            session.add(Scrape(user_id=user_id, url=url, payload=payload, scraped_at=now))
        await session.commit()
```

**Key decisions:**
- **User-level, not project-level**: If the same user scrapes `example.com` for Project A, that content is reusable in Project B. This cuts API calls significantly.
- **Upsert, not insert**: Re-scraping the same URL updates the cache instead of creating duplicates.
- **Store the full payload** (markdown + HTML + metadata), not just markdown. Different downstream consumers may need different formats.

**Scrape model:**
```python
class Scrape(Base):
    __tablename__ = "scrapes"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)  # Full scrape result
    scraped_at = Column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "url"),)
```

### Stage 3: Generate (Truncate + Compose + Validate)

Feed cached content into an LLM agent with three sub-steps:

#### 3a. Truncate

LLMs have context limits. Scraped content can be 500KB+. Always truncate before composing.

```python
MAX_SOURCE_CONTENT = 120_000  # chars, ~30K tokens for most models

def build_prompt(user_prompt: str, source_url: str | None,
                 source_markdown: str | None, source_html: str | None,
                 style: str = "minimal") -> str:
    parts = [f"User prompt: {user_prompt}", f"Preferred style: {style}"]

    if source_url:
        parts.append(f"Source URL: {source_url}")
    if source_markdown:
        parts.append("Source markdown:")
        parts.append(source_markdown[:MAX_SOURCE_CONTENT])
    if source_html:
        parts.append("Source HTML:")
        parts.append(source_html[:MAX_SOURCE_CONTENT])

    return "\n\n".join(parts)
```

**Key decisions:**
- **Truncate at char level**, not token level. Char truncation is instant; tokenization is model-specific and slow. 120K chars is a conservative proxy for ~30K tokens.
- **Include the URL even if you include the content**. The LLM uses the URL as a signal for the site's domain/purpose.
- **Separate markdown and HTML**. Markdown is better for content extraction; HTML is better for layout/style replication.

#### 3b. Compose

The prompt is assembled from parts, not a single template string. This makes it easy to add/remove sections without breaking the prompt structure.

#### 3c. Validate

The LLM output must match a Pydantic schema. No exceptions.

```python
from pydantic import BaseModel, Field

class GeneratedFile(BaseModel):
    path: str = Field(description="Relative path like index.html or assets/style.css")
    content: str = Field(description="UTF-8 file content")

class GeneratedSite(BaseModel):
    title: str
    description: str
    entrypoint: str = Field(default="index.html")
    files: list[GeneratedFile] = Field(default_factory=list)
```

Using Pydantic AI's `output_type` parameter on the Agent enforces this automatically — the agent retries or raises if the LLM output doesn't parse.

## Orchestration: Putting It Together

```python
async def crawl_and_generate(user_id: str, url: str, prompt: str, store, crawl_service, gen_service):
    # 1. Check cache
    cached = await store.get_scrape(user_id, url)

    if not cached:
        # 2. Crawl
        result = await crawl_service.scrape(url, formats=["markdown", "html"])
        await store.set_scrape(user_id, url, result)
        cached = result

    # 3. Generate (truncation happens inside build_prompt)
    markdown = cached.get("markdown", "")
    html = cached.get("html", "")
    site = await gen_service.generate(prompt, source_url=url,
                                       source_markdown=markdown, source_html=html)
    return site
```

## Pitfalls

1. **Scraping without caching**: You'll hit rate limits and slow down your UX. A user tweaking their prompt shouldn't trigger a re-scrape.

2. **Feeding raw HTML to the LLM**: Raw HTML is 3-10x larger than its markdown equivalent for the same content. Always prefer markdown; only include HTML when the downstream task needs layout info.

3. **No truncation**: A single large page can consume your entire context window. The LLM will either error or silently drop the overflow. Truncate explicitly.

4. **Coupling scrape format to generation**: If you only store markdown and later need HTML (e.g., for style extraction), you have to re-scrape. Store the full payload upfront.

5. **Project-level caching**: If users reuse the same source across projects, you're wasting API calls. Cache at user level.

6. **Sync scraping in an async handler**: One slow external scrape blocks your entire FastAPI server. Always use `asyncio.to_thread` or a native async HTTP client.

## When NOT to Use This Pattern

- **Real-time content**: If you need the latest version of a page on every request (e.g., monitoring), skip the cache or add a TTL.
- **Single-use scraping**: If you scrape once and never revisit, the cache layer is overhead. But most applications end up revisiting.
- **Authenticated/personalized pages**: Cached scrapes won't have the right session. You'll need per-session scraping, which changes the dedup key.

## Adapting This Pattern

| If you're using... | Replace... |
|---|---|
| Playwright instead of Firecrawl | The `_scrape_sync` internals. The async bridge and cache layer stay the same. |
| A different LLM framework | The agent/output_type validation. The prompt composition pattern stays the same. |
| Redis instead of PostgreSQL for cache | The `get_scrape`/`set_scrape` methods. Consider TTL-based expiry. |
| Multiple content types (PDF, video transcript) | Add a `content_type` field to the Scrape model and branch in `build_prompt`. |
