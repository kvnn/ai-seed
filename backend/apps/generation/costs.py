"""
AI Model cost calculation utilities.

Pricing data for various AI models. Prices are per token in USD.
Last updated: February 2026
"""
from dataclasses import dataclass
from typing import Optional

from backend.logger import logger


@dataclass
class ModelPricing:
    """Pricing per token for a model."""
    input_per_token: float  # USD per input token
    output_per_token: float  # USD per output token


@dataclass
class UsageInfo:
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_name: str
    cost_usd: float


# Pricing in USD per token (prices as of Feb 2026)
# Format: "provider:model" -> ModelPricing
MODEL_PRICING = {
    # OpenAI GPT-5 models
    "openai:gpt-5.2": ModelPricing(
        input_per_token=1.75 / 1_000_000,
        output_per_token=14.00 / 1_000_000,
    ),
    "openai:gpt-5.1": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    "openai:gpt-5": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    "openai:gpt-5-mini": ModelPricing(
        input_per_token=0.25 / 1_000_000,
        output_per_token=2.00 / 1_000_000,
    ),
    "openai:gpt-5-nano": ModelPricing(
        input_per_token=0.05 / 1_000_000,
        output_per_token=0.40 / 1_000_000,
    ),
    # OpenAI GPT-5 chat variants
    "openai:gpt-5.2-chat-latest": ModelPricing(
        input_per_token=1.75 / 1_000_000,
        output_per_token=14.00 / 1_000_000,
    ),
    "openai:gpt-5.1-chat-latest": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    "openai:gpt-5-chat-latest": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    # OpenAI GPT-5 codex variants
    "openai:gpt-5.2-codex": ModelPricing(
        input_per_token=1.75 / 1_000_000,
        output_per_token=14.00 / 1_000_000,
    ),
    "openai:gpt-5.1-codex-max": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    "openai:gpt-5.1-codex": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    "openai:gpt-5-codex": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    # OpenAI GPT-5 pro variants
    "openai:gpt-5.2-pro": ModelPricing(
        input_per_token=21.00 / 1_000_000,
        output_per_token=168.00 / 1_000_000,
    ),
    "openai:gpt-5-pro": ModelPricing(
        input_per_token=15.00 / 1_000_000,
        output_per_token=120.00 / 1_000_000,
    ),
    # OpenAI GPT-4 models
    "openai:gpt-4.1": ModelPricing(
        input_per_token=2.00 / 1_000_000,
        output_per_token=8.00 / 1_000_000,
    ),
    "openai:gpt-4.1-mini": ModelPricing(
        input_per_token=0.40 / 1_000_000,
        output_per_token=1.60 / 1_000_000,
    ),
    "openai:gpt-4.1-nano": ModelPricing(
        input_per_token=0.10 / 1_000_000,
        output_per_token=0.40 / 1_000_000,
    ),
    "openai:gpt-4o": ModelPricing(
        input_per_token=2.50 / 1_000_000,
        output_per_token=10.00 / 1_000_000,
    ),
    "openai:gpt-4o-mini": ModelPricing(
        input_per_token=0.15 / 1_000_000,
        output_per_token=0.60 / 1_000_000,
    ),
    "openai:gpt-4-turbo": ModelPricing(
        input_per_token=10.00 / 1_000_000,
        output_per_token=30.00 / 1_000_000,
    ),
    # OpenAI reasoning models
    "openai:o1": ModelPricing(
        input_per_token=15.00 / 1_000_000,
        output_per_token=60.00 / 1_000_000,
    ),
    "openai:o1-mini": ModelPricing(
        input_per_token=3.00 / 1_000_000,
        output_per_token=12.00 / 1_000_000,
    ),
    "openai:o3-mini": ModelPricing(
        input_per_token=1.10 / 1_000_000,
        output_per_token=4.40 / 1_000_000,
    ),
    # Anthropic models
    "anthropic:claude-3-5-sonnet-latest": ModelPricing(
        input_per_token=3.00 / 1_000_000,
        output_per_token=15.00 / 1_000_000,
    ),
    "anthropic:claude-3-5-haiku-latest": ModelPricing(
        input_per_token=0.80 / 1_000_000,
        output_per_token=4.00 / 1_000_000,
    ),
    "anthropic:claude-3-opus-latest": ModelPricing(
        input_per_token=15.00 / 1_000_000,
        output_per_token=75.00 / 1_000_000,
    ),
    # Google models
    "google:gemini-1.5-pro": ModelPricing(
        input_per_token=1.25 / 1_000_000,
        output_per_token=5.00 / 1_000_000,
    ),
    "google:gemini-1.5-flash": ModelPricing(
        input_per_token=0.075 / 1_000_000,
        output_per_token=0.30 / 1_000_000,
    ),
    "google:gemini-2.0-flash": ModelPricing(
        input_per_token=0.10 / 1_000_000,
        output_per_token=0.40 / 1_000_000,
    ),
}

# Fallback pricing for unknown models (conservative estimate)
FALLBACK_PRICING = ModelPricing(
    input_per_token=5.00 / 1_000_000,
    output_per_token=15.00 / 1_000_000,
)


def get_model_pricing(model_name: str) -> ModelPricing:
    """
    Get pricing for a model by name.

    Handles various name formats:
    - "openai:gpt-4o"
    - "gpt-4o" (assumes OpenAI)
    - "claude-3-5-sonnet-latest" (assumes Anthropic)
    """
    # Direct lookup
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]

    # Try with openai prefix
    openai_name = f"openai:{model_name}"
    if openai_name in MODEL_PRICING:
        return MODEL_PRICING[openai_name]

    # Try with anthropic prefix
    anthropic_name = f"anthropic:{model_name}"
    if anthropic_name in MODEL_PRICING:
        return MODEL_PRICING[anthropic_name]

    # Try partial matches
    model_lower = model_name.lower()
    for key, pricing in MODEL_PRICING.items():
        if model_lower in key.lower() or key.lower().split(":")[-1] in model_lower:
            return pricing

    logger.warning(f"[costs] Unknown model pricing for: {model_name}, using fallback")
    return FALLBACK_PRICING


def calculate_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    """Calculate USD cost for token usage."""
    pricing = get_model_pricing(model_name)
    cost = (
        prompt_tokens * pricing.input_per_token +
        completion_tokens * pricing.output_per_token
    )
    return round(cost, 6)


def extract_usage_from_result(result, model_name: str) -> Optional[UsageInfo]:
    """
    Extract usage information from a pydantic-ai result object.

    The result object from Agent.run() has a usage() method that returns
    usage information including token counts.
    """
    try:
        # pydantic-ai result has usage() method
        usage = result.usage()

        prompt_tokens = getattr(usage, 'request_tokens', 0) or getattr(usage, 'prompt_tokens', 0) or 0
        completion_tokens = getattr(usage, 'response_tokens', 0) or getattr(usage, 'completion_tokens', 0) or 0
        total_tokens = getattr(usage, 'total_tokens', None) or (prompt_tokens + completion_tokens)

        cost = calculate_cost(model_name, prompt_tokens, completion_tokens)

        return UsageInfo(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model_name=model_name,
            cost_usd=cost,
        )
    except Exception as e:
        logger.warning(f"[costs] Failed to extract usage from result: {e}")
        return None


def format_cost(cost_usd: float) -> str:
    """Format cost for display."""
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    elif cost_usd < 1.00:
        return f"${cost_usd:.3f}"
    else:
        return f"${cost_usd:.2f}"
