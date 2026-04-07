# Pattern: Dual-Extraction LLM Pipeline (Style vs Content)

## Problem

You need to extract structured information from external content, but the content has two fundamentally different dimensions — **visual/style** and **semantic/messaging** — that require different prompts, different source material, and different output schemas. Feeding everything into one prompt produces muddy results: the LLM hallucinates a vision statement from CSS colors, or infers a color palette from marketing copy.

## Pattern

Split extraction into two independent agents with distinct prompts and schemas, then merge results. Add a **generation fallback** for the semantic dimension when no content sources are available.

```
                    ┌─────────────────┐
                    │  Source Content  │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
          Style Sources            Content Sources
          (HTML, CSS)              (Markdown, text)
                 │                       │
                 ▼                       ▼
        ┌────────────────┐     ┌────────────────┐
        │ Style Extractor│     │Content Extractor│
        │                │     │                 │
        │ colors, imagery│     │ vision, values  │
        │ typography     │     │ differentiation │
        └───────┬────────┘     └───────┬─────────┘
                │                      │
                │    No content?       │
                │         │            │
                │         ▼            │
                │  ┌──────────────┐    │
                │  │  Generator   │    │
                │  │ (from keys/  │    │
                │  │  categories) │    │
                │  └──────┬───────┘    │
                │         │            │
                └─────────┴────────────┘
                          │
                          ▼
                   ┌──────────┐
                   │  Merged  │
                   │  Result  │
                   └──────────┘
```

### Why Two Agents, Not One

- **Different source material**: Style extraction needs HTML/CSS. Content extraction needs prose. Feeding CSS to a content extractor wastes tokens and confuses the model.
- **Different failure modes**: A missing color palette is a different problem than a missing vision statement. Separate agents let you handle each independently.
- **Different fallbacks**: When there's no prose content, you can generate messaging from keywords/categories. There's no equivalent fallback for style — you either have visual sources or you don't.

### The Schemas

Keep them separate. Each schema maps to one agent's output.

```python
from pydantic import BaseModel, Field

class ExtractedStyle(BaseModel):
    """Visual identity extracted from HTML/CSS sources."""
    brand_imagery: list[str] = Field(default_factory=list,
        description="3-5 descriptive terms for visual style")
    color_palette_hex: list[str] = Field(default_factory=list,
        description="3-6 primary colors as hex codes")
    coherence: str | None = Field(default=None,
        description="Visual consistency patterns")

class ExtractedContent(BaseModel):
    """Brand messaging extracted from prose sources."""
    vision: str | None = Field(default=None,
        description="Vision statement, 1-2 sentences")
    value: str | None = Field(default=None,
        description="Value proposition, 1-2 sentences")
    meaning: str | None = Field(default=None,
        description="What the brand stands for")
    differentiation: str | None = Field(default=None,
        description="What makes this brand unique")

class GeneratedContent(BaseModel):
    """Brand messaging generated from categories/keywords (fallback)."""
    vision: str = Field(description="Aspirational vision statement")
    value: str = Field(description="Customer-focused value proposition")
    meaning: str | None = None
    differentiation: str | None = None
```

**Key decisions:**
- **Style fields use `list` with `default_factory`**. If the LLM can't find colors, you get an empty list, not a validation error.
- **Content fields are all optional**. Not every source has a vision statement. Don't force the LLM to fabricate one.
- **Generated content fields are required**. When you're generating (not extracting), the whole point is to produce these fields.

### The Agents

One factory function per extraction type.

```python
from pydantic_ai import Agent

def build_style_extractor(model_name: str) -> Agent:
    return Agent(
        model_name,
        output_type=ExtractedStyle,
        instructions=[
            "Extract visual brand style from website content.",
            "Focus ONLY on: colors, typography, visual imagery style, layout.",
            "Do NOT infer messaging, vision, or value propositions.",
            "For colors, extract from CSS/HTML or infer from imagery descriptions.",
            "Use common hex codes. Return 3-6 primary colors.",
        ],
    )

def build_content_extractor(model_name: str) -> Agent:
    return Agent(
        model_name,
        output_type=ExtractedContent,
        instructions=[
            "Extract brand messaging and values from website content.",
            "Focus on: vision, mission, value proposition, meaning.",
            "Only include fields the content actually supports.",
            "Do NOT fabricate statements from style-only content.",
        ],
    )

def build_content_generator(model_name: str) -> Agent:
    return Agent(
        model_name,
        output_type=GeneratedContent,
        instructions=[
            "Generate brand messaging from business categories and keywords.",
            "Be specific to the domain — avoid generic platitudes.",
            "Vision should be aspirational. Value prop should be concrete.",
        ],
    )
```

### The Service

The service orchestrates source routing and fallback logic.

```python
class ExtractionService:
    def __init__(self, model_name: str):
        self._style_agent = build_style_extractor(model_name)
        self._content_agent = build_content_extractor(model_name)
        self._generator = build_content_generator(model_name)

    async def extract(
        self,
        style_sources: list[dict],
        content_sources: list[dict] | None = None,
        categories: list[str] | None = None,
        keywords: list[str] | None = None,
    ) -> dict:
        result = {}

        # Style extraction from visual sources
        if style_sources:
            style = await self._extract_style(style_sources)
            result.update(style)

        # Content extraction OR generation fallback
        if content_sources:
            content = await self._extract_content(content_sources)
            result.update(content)
        elif categories or keywords:
            content = await self._generate_from_context(categories, keywords)
            result.update(content)

        return result

    async def _extract_style(self, sources: list[dict]) -> dict:
        prompt = self._build_source_prompt(sources, include_html=True, max_chars=20_000)
        result = await self._style_agent.run(prompt)
        return result.output.model_dump(exclude_none=True)

    async def _extract_content(self, sources: list[dict]) -> dict:
        prompt = self._build_source_prompt(sources, include_html=False, max_chars=30_000)
        result = await self._content_agent.run(prompt)
        return result.output.model_dump(exclude_none=True)

    async def _generate_from_context(
        self, categories: list[str] | None, keywords: list[str] | None,
    ) -> dict:
        parts = []
        if categories:
            parts.append(f"Categories: {', '.join(categories)}")
        if keywords:
            parts.append(f"Keywords: {', '.join(keywords)}")
        result = await self._generator.run("\n".join(parts))
        return result.output.model_dump(exclude_none=True)

    def _build_source_prompt(
        self, sources: list[dict], include_html: bool, max_chars: int,
    ) -> str:
        parts = []
        for src in sources:
            parts.append(f"--- Source: {src.get('url', 'Unknown')} ---")
            if include_html and src.get("html"):
                parts.append(src["html"][:max_chars])
            if src.get("markdown"):
                parts.append(src["markdown"][:max_chars])
        return "\n\n".join(parts)
```

**Key decisions:**
- **`model_dump(exclude_none=True)`** — Only merge fields the LLM actually populated. This prevents overwriting style results with `None` content fields.
- **Different truncation limits** — Style extraction gets 20K chars (CSS is dense). Content extraction gets 30K chars (prose is verbose). Match limits to the task.
- **Fallback is explicit** — The `elif` makes it clear: extract from content if available, otherwise generate from context. Never both.

## Pitfalls

1. **Single-prompt extraction**: Asking one agent to extract both colors and vision from mixed sources produces unreliable results. The model conflates the two dimensions.

2. **Forcing required fields on extraction**: If you make `vision` required in the extraction schema, the LLM will fabricate one from a CSS file. Optional fields with `exclude_none` are the correct approach.

3. **No generation fallback**: If there are no content sources and no fallback, the result has no messaging at all. Categories and keywords are often available even when prose isn't.

4. **Merging with `None` overwrites**: If you naively `result.update(content_dict)` and the content dict has `{"vision": None}`, it overwrites a previously extracted vision. Use `exclude_none=True`.

5. **Truncating HTML the same as markdown**: HTML is 3-10x more verbose than markdown for the same content. Use lower limits for HTML, higher for markdown.

## When NOT to Use This Pattern

- **Single-dimension extraction**: If you only need colors OR messaging (not both), one agent is sufficient.
- **Homogeneous sources**: If all sources are the same type (e.g., all markdown blog posts), there's no style/content split to make.
- **Real-time extraction**: If latency matters, running two agents sequentially doubles the wait. Consider running them concurrently with `asyncio.gather`.

## Adapting This Pattern

| If you're extracting... | Replace... |
|---|---|
| Technical specs + marketing copy | The two schemas. One for specs (versions, features, compatibility), one for positioning (benefits, differentiators). |
| Audio + visual from media | The source routing. Audio sources → transcript agent, visual sources → image description agent. |
| Structured data + narrative from reports | The prompts. One agent extracts tables/numbers, another extracts conclusions/recommendations. |
| Using LangChain instead of Pydantic AI | The agent factory. Use `with_structured_output()` for schema enforcement. The dual-agent pattern stays the same. |
