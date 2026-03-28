import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException

from backend.apps.generation.agents import build_site_generator
from backend.apps.generation.costs import UsageInfo, calculate_cost, extract_usage_from_result
from backend.apps.generation.schemas import GeneratedSite
from backend.logger import logger
from backend.storage import StorageBackend


@dataclass
class GenerationResult:
    """Result of site generation including usage info."""
    site: GeneratedSite
    usage: Optional[UsageInfo] = None


@dataclass
class StreamingUpdate:
    """Update during streaming generation."""
    type: str  # 'generating', 'partial_file', 'complete'
    tokens_so_far: int = 0
    partial_content: Optional[str] = None
    file_name: Optional[str] = None
    files_complete: int = 0
    files_total: int = 0


class SiteGenerationService:
    def __init__(self, model_name: str, storage: Optional[StorageBackend] = None):
        self._model_name = model_name
        self._agent = build_site_generator(model_name)
        self._storage = storage

    def model_name(self) -> str:
        return self._model_name

    def _build_prompt_parts(
        self,
        prompt: str,
        source_url: Optional[str],
        source_markdown: Optional[str],
        source_html: Optional[str],
        preferred_style: Optional[str] = None,
    ) -> str:
        """Build the full prompt from parts."""
        style = preferred_style or "minimal editorial"
        parts: List[str] = []
        parts.append(f"User prompt: {prompt}")
        parts.append(f"Preferred style: {style}")
        if source_url:
            parts.append(f"Source URL: {source_url}")
        if source_markdown:
            parts.append("Source markdown:")
            parts.append(source_markdown[:120000])
        if source_html:
            parts.append("Source html:")
            parts.append(source_html[:120000])
        return "\n\n".join(parts)

    async def generate(
        self,
        prompt: str,
        source_url: Optional[str],
        source_markdown: Optional[str],
        source_html: Optional[str],
        preferred_style: Optional[str] = None,
    ) -> GenerationResult:
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")

        full_prompt = self._build_prompt_parts(
            prompt, source_url, source_markdown, source_html, preferred_style
        )

        try:
            res = await self._agent.run(full_prompt)

            # Extract usage information
            usage = extract_usage_from_result(res, self._model_name)
            if usage:
                logger.info(
                    "[site_generation] usage: model=%s prompt=%d completion=%d total=%d cost=$%.4f",
                    usage.model_name,
                    usage.prompt_tokens,
                    usage.completion_tokens,
                    usage.total_tokens,
                    usage.cost_usd,
                )

            return GenerationResult(site=res.output, usage=usage)
        except Exception as e:
            logger.error(f"[site_generation] site generation failed: {e}")
            raise HTTPException(status_code=500, detail="site_generation_failed")

    async def generate_streaming(
        self,
        prompt: str,
        source_url: Optional[str],
        source_markdown: Optional[str],
        source_html: Optional[str],
        preferred_style: Optional[str] = None,
        on_progress: Optional[Callable[[StreamingUpdate], Any]] = None,
        throttle_ms: int = 100,
    ) -> GenerationResult:
        """
        Generate a site with streaming progress updates.

        Yields progress updates via on_progress callback as tokens are generated.
        The throttle_ms parameter controls how often updates are sent.
        """
        if not os.getenv("OPENAI_API_KEY"):
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY is not configured")

        full_prompt = self._build_prompt_parts(
            prompt, source_url, source_markdown, source_html, preferred_style
        )

        try:
            last_update_time = 0
            tokens_generated = 0

            async with self._agent.run_stream(full_prompt) as result:
                # Stream structured output with debouncing
                async for partial, last in result.stream_structured(debounce_by=throttle_ms / 1000):
                    tokens_generated += 1  # Approximate - actual token count comes at end

                    current_time = time.time() * 1000
                    if on_progress and (current_time - last_update_time >= throttle_ms or last):
                        last_update_time = current_time

                        # Try to extract partial file info if available
                        file_name = None
                        partial_content = None
                        files_complete = 0

                        if hasattr(partial, "files") and partial.files:
                            files_complete = len(partial.files)
                            if partial.files:
                                last_file = partial.files[-1]
                                file_name = getattr(last_file, "path", None)
                                content = getattr(last_file, "content", "")
                                if content:
                                    partial_content = content[-150:] if len(content) > 150 else content

                        update = StreamingUpdate(
                            type="partial_file" if file_name else "generating",
                            tokens_so_far=tokens_generated,
                            file_name=file_name,
                            partial_content=partial_content,
                            files_complete=files_complete,
                        )

                        if asyncio.iscoroutinefunction(on_progress):
                            await on_progress(update)
                        else:
                            on_progress(update)

                # Get final result
                site = await result.get_output()

                # Get usage from the result
                usage = None
                try:
                    usage_data = result.usage()
                    prompt_tokens = getattr(usage_data, "request_tokens", 0) or getattr(usage_data, "prompt_tokens", 0) or 0
                    completion_tokens = getattr(usage_data, "response_tokens", 0) or getattr(usage_data, "completion_tokens", 0) or 0
                    total_tokens = getattr(usage_data, "total_tokens", None) or (prompt_tokens + completion_tokens)
                    cost = calculate_cost(self._model_name, prompt_tokens, completion_tokens)

                    usage = UsageInfo(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                        model_name=self._model_name,
                        cost_usd=cost,
                    )

                    logger.info(
                        "[site_generation] streaming usage: model=%s prompt=%d completion=%d total=%d cost=$%.4f",
                        usage.model_name,
                        usage.prompt_tokens,
                        usage.completion_tokens,
                        usage.total_tokens,
                        usage.cost_usd,
                    )
                except Exception as exc:
                    logger.warning("[site_generation] failed to extract streaming usage error=%s", str(exc))

                return GenerationResult(site=site, usage=usage)

        except Exception as exc:
            logger.error("[site_generation] streaming generation failed error=%s", str(exc))
            raise HTTPException(status_code=500, detail="site_generation_failed")

    def write_site(self, output_dir: Path, run_id: str, site: GeneratedSite, build_id: Optional[str] = None) -> Dict[str, Any]:
        """Write generated site files to storage.

        Uses the storage backend if available, otherwise falls back to local filesystem.
        """
        # Determine the base key/path for site files
        if build_id:
            site_prefix = f"runs/{run_id}/builds/{build_id}/site"
        else:
            site_prefix = f"runs/{run_id}/site"

        written: List[str] = []

        if self._storage:
            # Use storage abstraction
            for f in site.files:
                rel = f.path.strip().lstrip("/").replace("\\", "/")
                if not rel:
                    continue
                # Validate path doesn't escape site directory
                if ".." in rel or rel.startswith("/"):
                    raise HTTPException(status_code=400, detail="site_generation_failed:invalid_path")

                key = f"{site_prefix}/{rel}"
                self._storage.write_file(key, f.content)
                written.append(rel)
        else:
            # Legacy: write to local filesystem directly
            run_dir = output_dir / "runs" / run_id
            if build_id:
                site_dir = run_dir / "builds" / build_id / "site"
            else:
                site_dir = run_dir / "site"
            site_dir.mkdir(parents=True, exist_ok=True)

            for f in site.files:
                rel = f.path.strip().lstrip("/").replace("\\", "/")
                if not rel:
                    continue
                target = (site_dir / rel).resolve()
                if not str(target).startswith(str(site_dir.resolve())):
                    raise HTTPException(status_code=400, detail="site_generation_failed:invalid_path")

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.content, encoding="utf-8")
                written.append(rel)

        entrypoint = site.entrypoint.strip().lstrip("/").replace("\\", "/")
        if not entrypoint:
            entrypoint = "index.html"

        if build_id:
            preview_url = f"/preview/runs/{run_id}/builds/{build_id}/site/{entrypoint}"
        else:
            preview_url = f"/preview/runs/{run_id}/site/{entrypoint}"

        return {
            "run_id": run_id,
            "build_id": build_id,
            "preview_url": preview_url,
            "entrypoint": entrypoint,
            "files": sorted(set(written)),
            "title": site.title,
            "description": site.description,
        }

    async def write_site_to_version(
        self,
        store: "DBProjectStore",
        project_id: str,
        version_id: str,
        site: GeneratedSite,
    ) -> Dict[str, Any]:
        """
        Write generated site files to VersionFile table (v0.4.0+).
        Returns version summary with file list.
        """
        files = []
        for f in site.files:
            rel = f.path.strip().lstrip("/").replace("\\", "/")
            if not rel:
                continue
            if ".." in rel or rel.startswith("/"):
                raise HTTPException(status_code=400, detail="site_generation_failed:invalid_path")

            files.append({
                "filename": rel,
                "content": f.content,
            })

        entrypoint = site.entrypoint.strip().lstrip("/").replace("\\", "/")
        if not entrypoint:
            entrypoint = "index.html"

        # Write files to DB and update version metadata
        result = await store.write_version_files(
            project_id=project_id,
            version_id=version_id,
            files=files,
            title=site.title,
            description=site.description,
            entrypoint=entrypoint,
        )

        return result
