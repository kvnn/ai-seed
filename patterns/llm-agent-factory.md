# Pattern: LLM Agent Factory with Cost Tracking

## Problem

You need to call LLMs in multiple places (site generation, keyword extraction, brand analysis, title generation...) and each call needs:
- A structured output schema (not free-text)
- Token usage tracking for billing/monitoring
- The ability to swap models without rewriting call sites

Without a pattern, you end up with ad-hoc `openai.chat.completions.create()` calls scattered through your codebase, each with its own error handling, usage extraction, and output parsing.

## Pattern

Use a **factory function** that returns a configured agent, and a **cost tracking layer** that sits between the agent and your persistence.

```
┌──────────────┐    ┌───────────┐    ┌──────────────┐
│ Agent Factory │───>│   Agent   │───>│ Cost Tracker │
│              │    │           │    │              │
│ model_name   │    │ run()     │    │ extract_usage│
│ output_type  │    │ run_stream│    │ calculate    │
│ instructions │    │ ()        │    │ persist      │
└──────────────┘    └───────────┘    └──────────────┘
```

### The Factory

One function per agent type. Each returns a configured agent with a Pydantic output schema.

```python
from pydantic_ai import Agent
from your_app.schemas import GeneratedSite

def build_site_generator(model_name: str) -> Agent:
    return Agent(
        model_name,
        output_type=GeneratedSite,
        instructions=[
            """You generate static websites as flat files.

            Output rules:
            - Always include index.html and styles.css
            - Files must be self-contained (no CDN links)
            - Keep total output small (< 250KB)
            """
        ],
    )
```

```python
from your_app.schemas import GeneratedKeywords

def build_keyword_generator(model_name: str) -> Agent:
    return Agent(
        model_name,
        output_type=GeneratedKeywords,
        instructions=[
            "Generate SEO keywords based on the provided content and categories.",
            "Return 5-15 keywords, ordered by relevance.",
        ],
    )
```

**Key decisions:**
- **One factory per task type**, not a universal "make me an agent" function. Each agent has different instructions and output schemas.
- **`output_type` is a Pydantic model**. The framework handles JSON schema enforcement, retry on parse failure, and type validation. You never manually parse LLM JSON.
- **Instructions as a list of strings**, not a single block. Easier to compose, test, and modify individual sections.
- **Model name is a parameter**, not hardcoded. Lets you swap models per-environment or per-user-tier.

### The Output Schema

Keep schemas minimal. Only include fields the LLM needs to produce.

```python
from pydantic import BaseModel, Field

class GeneratedFile(BaseModel):
    path: str = Field(description="Relative path like index.html")
    content: str = Field(description="UTF-8 file content")

class GeneratedSite(BaseModel):
    title: str
    description: str
    entrypoint: str = Field(default="index.html")
    files: list[GeneratedFile] = Field(default_factory=list)

class GeneratedKeywords(BaseModel):
    keywords: list[str] = Field(description="SEO keywords ordered by relevance")
```

**Key decisions:**
- **Field descriptions guide the LLM**. Pydantic AI sends the schema (including descriptions) to the model. Good descriptions = better output.
- **Defaults for optional fields**. If the LLM omits `entrypoint`, you get `"index.html"` instead of a validation error.
- **No nested complexity**. If you need deep nesting, the LLM will struggle. Flatten where possible.

### The Service Layer

Wrap the agent in a service that handles prompt composition and usage extraction.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class GenerationResult:
    output: GeneratedSite
    usage: Optional[UsageInfo] = None

class SiteGenerationService:
    def __init__(self, model_name: str):
        self._model_name = model_name
        self._agent = build_site_generator(model_name)

    async def generate(self, prompt: str, **context) -> GenerationResult:
        full_prompt = self._build_prompt(prompt, **context)
        result = await self._agent.run(full_prompt)

        usage = extract_usage(result, self._model_name)
        if usage:
            logger.info("[generation] model=%s tokens=%d cost=$%.4f",
                        usage.model_name, usage.total_tokens, usage.cost_usd)

        return GenerationResult(output=result.output, usage=usage)

    def _build_prompt(self, prompt: str, **context) -> str:
        parts = [f"User prompt: {prompt}"]
        for key, value in context.items():
            if value:
                parts.append(f"{key}: {value}")
        return "\n\n".join(parts)
```

### Cost Tracking

Track every LLM call's token usage and cost. This is non-negotiable for production.

```python
from dataclasses import dataclass

@dataclass
class ModelPricing:
    input_per_token: float   # USD
    output_per_token: float  # USD

@dataclass
class UsageInfo:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str
    cost_usd: float

# Pricing table (update when models change)
MODEL_PRICING = {
    "openai:gpt-4o": ModelPricing(
        input_per_token=2.50 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    "anthropic:claude-3-5-sonnet-latest": ModelPricing(
        input_per_token=3.00 / 1_000_000,
        output_per_token=15.00 / 1_000_000,
    ),
    # ... add models as needed
}

FALLBACK_PRICING = ModelPricing(
    input_per_token=5.00 / 1_000_000,
    output_per_token=15.00 / 1_000_000,
)


def get_pricing(model_name: str) -> ModelPricing:
    """Lookup with fallback. Handles 'gpt-4o' and 'openai:gpt-4o' formats."""
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]
    # Try common prefixes
    for prefix in ("openai:", "anthropic:", "google:"):
        prefixed = f"{prefix}{model_name}"
        if prefixed in MODEL_PRICING:
            return MODEL_PRICING[prefixed]
    logger.warning("[costs] unknown model %s, using fallback pricing", model_name)
    return FALLBACK_PRICING


def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = get_pricing(model_name)
    return round(
        prompt_tokens * pricing.input_per_token +
        completion_tokens * pricing.output_per_token,
        6,
    )


def extract_usage(result, model_name: str) -> UsageInfo | None:
    """Extract usage from a pydantic-ai result object."""
    try:
        usage = result.usage()
        prompt_tokens = getattr(usage, 'request_tokens', 0) or getattr(usage, 'prompt_tokens', 0) or 0
        completion_tokens = getattr(usage, 'response_tokens', 0) or getattr(usage, 'completion_tokens', 0) or 0
        total_tokens = getattr(usage, 'total_tokens', None) or (prompt_tokens + completion_tokens)

        return UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model_name=model_name,
            cost_usd=calculate_cost(model_name, prompt_tokens, completion_tokens),
        )
    except Exception as e:
        logger.warning("[costs] failed to extract usage: %s", e)
        return None
```

**Key decisions:**
- **`getattr` with fallback chains**: Different LLM providers use different field names (`request_tokens` vs `prompt_tokens`). Handle both.
- **Fallback pricing**: Unknown models get conservative (high) pricing so you never undercount.
- **Cost stored per-generation in DB**: Enables per-user billing, budget alerts, and model cost comparison.

### Persisting Usage

Store usage on the entity that triggered the generation:

```python
# After generation completes
if usage:
    await store.update_version(
        version_id=version_id,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cost_usd=usage.cost_usd,
        model_name=usage.model_name,
    )
```

## Multi-Agent Pipelines

For complex tasks, chain multiple agents:

```
User Input
    │
    ▼
┌─────────────┐    ┌─────────────┐    ┌──────────────┐
│ SEO Agent   │───>│ Brand Agent │───>│ Site Generator│
│             │    │             │    │              │
│ Keywords    │    │ Colors,     │    │ Full site    │
│ Titles      │    │ Voice,      │    │ files        │
│             │    │ Imagery     │    │              │
└─────────────┘    └─────────────┘    └──────────────┘
```

Each agent has its own factory, schema, and instructions. The pipeline orchestrator passes outputs downstream:

```python
async def full_pipeline(user_prompt, source_content):
    # Step 1: SEO
    seo = await seo_service.generate_keywords(user_prompt, source_content[:50_000])

    # Step 2: Brand
    brand = await brand_service.extract_brand(source_content[:50_000])

    # Step 3: Generate (with SEO + Brand context)
    site = await gen_service.generate(
        prompt=user_prompt,
        keywords=", ".join(seo.keywords),
        brand_colors=brand.colors,
        brand_voice=brand.voice,
        source_markdown=source_content,
    )
    return site
```

**Key decision:** Each step truncates independently. The SEO agent gets 50KB of content. The site generator gets 120KB. Match the truncation to the task's needs.

## Pitfalls

1. **No output schema**: Free-text LLM output is unparseable in production. Always use structured output with Pydantic validation.

2. **Ignoring token usage**: Without tracking, you'll get a surprise bill. Log every call, store every cost.

3. **Hardcoded model names**: When you need to switch from GPT-4o to Claude, you don't want to grep-replace across 15 files. Pass the model name as a parameter.

4. **Giant instruction blocks**: A 2000-word system prompt is hard to maintain. Use a list of focused instruction strings. Each one addresses one concern.

5. **No fallback pricing**: An unknown model with no pricing entry silently reports $0 cost. Use conservative fallback pricing.

6. **Parsing usage across providers**: OpenAI says `prompt_tokens`, Anthropic says `request_tokens`, Google says something else. The `getattr` chain handles this.

## When NOT to Use This Pattern

- **One-off scripts**: If you're calling an LLM once in a migration script, just call it directly.
- **Unstructured output**: If you genuinely need free-text (creative writing, open-ended chat), a Pydantic output type adds friction.
- **Simple wrappers**: If you only have one agent and one model, the factory adds no value. Just instantiate directly.

## Adapting This Pattern

| If you're using... | Replace... |
|---|---|
| LangChain instead of Pydantic AI | The Agent class. Use LangChain's `with_structured_output()` for schema enforcement. |
| Direct OpenAI SDK | The agent abstraction. Use `response_format={"type": "json_schema", "json_schema": ...}` with Pydantic's `.model_json_schema()`. |
| A different cost source | The `MODEL_PRICING` dict. Pull from your billing API or a shared config service. |
| Multiple models per agent | Add a `model_name` parameter to the service's `generate()` method and rebuild the agent per-call (or cache by model name). |
