from typing import Any

try:
    from pydantic_ai import Agent as PydanticAgent
except ImportError:  # pragma: no cover - optional dependency
    PydanticAgent = None

from backend.apps.generation.prompts import SITE_GENERATOR_PROMPT
from backend.apps.generation.schemas import GeneratedSite


def _require_agent() -> Any:
    if PydanticAgent is None:
        raise RuntimeError("pydantic_ai is required to use backend.apps.generation")
    return PydanticAgent


def build_site_generator(model_name: str) -> Any:
    return _require_agent()(
        model_name,
        output_type=GeneratedSite,
        instructions=[SITE_GENERATOR_PROMPT],
    )
