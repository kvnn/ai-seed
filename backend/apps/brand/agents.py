from typing import Any

try:
    from pydantic_ai import Agent as PydanticAgent
except ImportError:  # pragma: no cover - optional dependency
    PydanticAgent = None

from backend.apps.brand.prompts import BRAND_EXTRACTOR_PROMPT, CONTENT_BRAND_GENERATOR_PROMPT
from backend.apps.brand.schemas import ExtractedBrandKit, GeneratedBrandContent


def _require_agent() -> Any:
    if PydanticAgent is None:
        raise RuntimeError("pydantic_ai is required to use backend.apps.brand")
    return PydanticAgent


def build_brand_extractor(model_name: str) -> Any:
    return _require_agent()(
        model_name,
        output_type=ExtractedBrandKit,
        instructions=[BRAND_EXTRACTOR_PROMPT],
    )


def build_content_brand_generator(model_name: str) -> Any:
    return _require_agent()(
        model_name,
        output_type=GeneratedBrandContent,
        instructions=[CONTENT_BRAND_GENERATOR_PROMPT],
    )
