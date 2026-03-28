"""
SSE streaming utilities for generation progress.

This module provides Server-Sent Events (SSE) support for streaming
generation progress to the frontend.
"""
import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi.responses import StreamingResponse

from backend.logger import logger


# Global storage for active generation queues
_generation_queues: Dict[str, asyncio.Queue] = {}


async def get_or_create_queue(run_id: str) -> asyncio.Queue:
    """Get or create a queue for a run."""
    if run_id not in _generation_queues:
        _generation_queues[run_id] = asyncio.Queue()
    return _generation_queues[run_id]


def remove_queue(run_id: str) -> None:
    """Remove a queue for a run."""
    _generation_queues.pop(run_id, None)


async def push_event(run_id: str, event: Dict[str, Any]) -> None:
    """Push an event to a run's queue."""
    if run_id in _generation_queues:
        await _generation_queues[run_id].put(event)


async def sse_generator(
    run_id: str,
    timeout: float = 30.0,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events from a run's queue.

    Event types:
    - {"type": "thinking", "message": "..."}
    - {"type": "generating", "tokens": 123, "file": "index.html", "content_tail": "..."}
    - {"type": "writing_code", "file": "index.html", "tail": "last 50 chars"}
    - {"type": "complete", "files": ["index.html", "styles.css"]}
    - {"type": "error", "message": "..."}
    - {"type": "keepalive"}
    """
    queue = await get_or_create_queue(run_id)

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=timeout)
                event_data = json.dumps(event)
                yield f"data: {event_data}\n\n"

                # Stop on terminal events
                if event.get("type") in ("complete", "error", "done"):
                    break
            except asyncio.TimeoutError:
                # Send keepalive
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
            except Exception as e:
                logger.error("[sse] error in generator: %s", str(e))
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    finally:
        # Clean up queue after streaming ends
        remove_queue(run_id)


def create_sse_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    """Create an SSE streaming response."""
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class StreamingProgressCallback:
    """
    Callback handler for streaming generation progress.

    Usage:
        callback = StreamingProgressCallback(run_id)
        await gen.generate_with_progress(prompt, callback=callback.on_progress)
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self._current_file: Optional[str] = None

    async def on_progress(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle a progress event."""
        event = {"type": event_type, **data}
        await push_event(self.run_id, event)

    async def thinking(self, message: str) -> None:
        """Report thinking/planning progress."""
        await self.on_progress("thinking", {"message": message})

    async def writing_file(self, filename: str, content_tail: str = "") -> None:
        """Report file writing progress."""
        self._current_file = filename
        await self.on_progress("writing_code", {
            "file": filename,
            "tail": content_tail[-100:] if content_tail else "",
        })

    async def complete(self, files: list, usage: dict = None) -> None:
        """Report generation complete with optional usage info."""
        data = {"files": files}
        if usage:
            data["usage"] = usage
        await self.on_progress("complete", data)

    async def error(self, message: str) -> None:
        """Report an error."""
        await self.on_progress("error", {"message": message})

    async def generating(
        self,
        tokens: int,
        file_name: Optional[str] = None,
        content_tail: Optional[str] = None,
        files_complete: int = 0,
    ) -> None:
        """Report streaming generation progress."""
        data = {"tokens": tokens, "files_complete": files_complete}
        if file_name:
            data["file"] = file_name
        if content_tail:
            data["content_tail"] = content_tail[-100:]
        await self.on_progress("generating", data)
