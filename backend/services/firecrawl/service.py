import json
import asyncio
from typing import Any, Dict, List, Optional

from backend.logger import logger

try:
    from firecrawl import Firecrawl
except ImportError:  # pragma: no cover - optional dependency
    Firecrawl = None


class FirecrawlService:
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        if Firecrawl is None:
            raise RuntimeError("firecrawl is required to use backend.services.firecrawl")
        kwargs: Dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = Firecrawl(**kwargs)
        logger.info("[firecrawl_service] initialized client base_url=%s", base_url or "default")

    def _summarize(self, result: Any, limit: int = 800) -> str:
        try:
            raw = json.dumps(result, default=str)
        except Exception:
            raw = repr(result)
        if len(raw) > limit:
            return f"{raw[:limit]}... (truncated)"
        return raw

    async def scrape(
        self,
        url: str,
        formats: Optional[List[Any]] = None,
        only_main_content: Optional[bool] = None,
    ) -> Any:
        return await asyncio.to_thread(self._scrape_sync, url, formats, only_main_content)

    def _scrape_sync(
        self,
        url: str,
        formats: Optional[List[Any]] = None,
        only_main_content: Optional[bool] = None,
    ) -> Any:
        logger.info("[firecrawl_service] scrape request url=%s formats=%s only_main_content=%s", url, formats, only_main_content)
        try:
            kwargs: Dict[str, Any] = {}
            if formats is not None:
                kwargs["formats"] = formats
            if only_main_content is not None:
                kwargs["only_main_content"] = only_main_content
            res = self._client.scrape(url, **kwargs)
            logger.info("[firecrawl_service] scrape response url=%s summary=%s", url, self._summarize(res))
            return res
        except Exception as e:
            logger.exception("[firecrawl_service] scrape failed url=%s error=%s", url, e)
            raise

    async def map(
        self,
        url: str,
        limit: Optional[int] = None,
        sitemap: Optional[str] = None,
        search: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return await asyncio.to_thread(self._map_sync, url, limit, sitemap, search, location)

    def _map_sync(
        self,
        url: str,
        limit: Optional[int] = None,
        sitemap: Optional[str] = None,
        search: Optional[str] = None,
        location: Optional[Dict[str, Any]] = None,
    ) -> Any:
        logger.info("[firecrawl_service] map request url=%s limit=%s sitemap=%s search=%s", url, limit, sitemap, search)
        try:
            kwargs: Dict[str, Any] = {}
            if limit is not None:
                kwargs["limit"] = limit
            if sitemap is not None:
                kwargs["sitemap"] = sitemap
            if search is not None:
                kwargs["search"] = search
            if location is not None:
                kwargs["location"] = location
            res = self._client.map(url=url, **kwargs)
            logger.info("[firecrawl_service] map response url=%s summary=%s", url, self._summarize(res))
            return res
        except Exception as e:
            logger.exception("[firecrawl_service] map failed url=%s error=%s", url, e)
            raise

    async def extract(
        self,
        urls: Optional[List[str]] = None,
        prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        enable_web_search: Optional[bool] = None,
    ) -> Any:
        return await asyncio.to_thread(self._extract_sync, urls, prompt, schema, enable_web_search)

    def _extract_sync(
        self,
        urls: Optional[List[str]] = None,
        prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None,
        enable_web_search: Optional[bool] = None,
    ) -> Any:
        logger.info("[firecrawl_service] extract request urls=%s prompt=%s schema_keys=%s", urls, (prompt or "")[:80], list(schema.keys()) if isinstance(schema, dict) else None)
        try:
            kwargs: Dict[str, Any] = {}
            if urls is not None:
                kwargs["urls"] = urls
            if prompt is not None:
                kwargs["prompt"] = prompt
            if schema is not None:
                kwargs["schema"] = schema
            if enable_web_search is not None:
                kwargs["enable_web_search"] = enable_web_search
            res = self._client.extract(**kwargs)
            logger.info("[firecrawl_service] extract response summary=%s", self._summarize(res))
            return res
        except Exception as e:
            logger.exception("[firecrawl_service] extract failed urls=%s error=%s", urls, e)
            raise
