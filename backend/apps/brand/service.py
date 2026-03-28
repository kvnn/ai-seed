from typing import Any, Dict, List, Optional

from backend.apps.brand.agents import (
    build_brand_extractor,
    build_content_brand_generator,
)
from backend.config import settings
from backend.logger import logger


class BrandService:
    """Service for brand identity extraction and management"""

    def __init__(self):
        self._agent = build_brand_extractor(settings.generator_model)
        self._content_agent = build_content_brand_generator(settings.generator_model)

    async def extract_brand_kit(
        self,
        style_sources: List[Dict[str, Any]],
        content_sources: Optional[List[Dict[str, Any]]] = None,
        categories: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract brand identity from source content.

        Args:
            style_sources: Sources for visual style (style_only, style_content)
            content_sources: Sources for content/messaging (content_only, style_content)
            categories: SEO categories (fallback for vision/value if no content sources)
            keywords: SEO keywords (fallback for vision/value if no content sources)

        Returns:
            Dict with brand kit fields
        """
        result = {}

        # Extract style elements (colors, imagery) from style sources
        if style_sources:
            style_data = await self._extract_style(style_sources)
            result.update(style_data)

        # Extract content elements (vision, value, etc.) from content sources
        # OR generate from categories/keywords if no content sources
        if content_sources:
            content_data = await self._extract_content(content_sources)
            result.update(content_data)
        elif categories or keywords:
            content_data = await self._generate_content_from_context(categories, keywords)
            result.update(content_data)

        return result

    async def _extract_style(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract visual style elements from sources."""
        parts = ["Extract visual brand style from the following website content:\n"]
        parts.append("Focus ONLY on: colors, typography, visual imagery style, layout patterns.\n")
        parts.append("Do NOT infer messaging, vision, or value propositions.\n")

        for src in sources:
            parts.append(f"\n--- Source: {src.get('url', 'Unknown')} ---\n")

            if src.get("html"):
                html = src["html"][:20000]
                parts.append(f"HTML/CSS:\n{html}\n")

            if src.get("markdown"):
                md = src["markdown"][:10000]
                parts.append(f"Content (for visual context):\n{md}\n")

        prompt = "\n".join(parts)

        logger.info("[brand_service] extracting style from %d sources", len(sources))

        try:
            result = await self._agent.run(prompt)
            brand_kit = result.output

            return {
                "brand_imagery": brand_kit.brand_imagery,
                "color_palette_hex": brand_kit.color_palette_hex,
                "coherence": brand_kit.coherence,
                "flexibility": brand_kit.flexibility,
            }
        except Exception as e:
            logger.exception("[brand_service] style extraction failed: %s", str(e))
            raise

    async def _extract_content(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract content/messaging elements from sources."""
        parts = ["Extract brand messaging and values from the following website content:\n"]
        parts.append("Focus on: vision, mission, value proposition, brand meaning, authenticity.\n")

        for src in sources:
            parts.append(f"\n--- Source: {src.get('url', 'Unknown')} ---\n")

            if src.get("markdown"):
                md = src["markdown"][:30000]
                parts.append(f"Content:\n{md}\n")

        prompt = "\n".join(parts)

        logger.info("[brand_service] extracting content from %d sources", len(sources))

        try:
            result = await self._agent.run(prompt)
            brand_kit = result.output

            return {
                "vision": brand_kit.vision,
                "meaning": brand_kit.meaning,
                "authenticity": brand_kit.authenticity,
                "differentiation": brand_kit.differentiation,
                "sustainability": brand_kit.sustainability,
                "commitment": brand_kit.commitment,
                "value": brand_kit.value,
            }
        except Exception as e:
            logger.exception("[brand_service] content extraction failed: %s", str(e))
            raise

    async def _generate_content_from_context(
        self,
        categories: Optional[List[str]],
        keywords: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Generate vision/value from categories and keywords when no content sources."""
        prompt = "Generate brand vision and value proposition based on:\n"

        if categories:
            prompt += f"\nCategories: {', '.join(categories)}"
        if keywords:
            prompt += f"\nKeywords: {', '.join(keywords)}"

        prompt += "\n\nCreate compelling, professional brand messaging that fits these themes."

        logger.info("[brand_service] generating content from categories/keywords")

        try:
            result = await self._content_agent.run(prompt)
            content = result.output

            return {
                "vision": content.vision,
                "meaning": content.meaning,
                "value": content.value,
                "differentiation": content.differentiation,
            }
        except Exception as e:
            logger.exception("[brand_service] content generation failed: %s", str(e))
            raise
