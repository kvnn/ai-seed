# Pattern: SSE Streaming for Long LLM Operations

## Problem

LLM generation takes 10-60+ seconds. Without real-time feedback, users stare at a spinner and wonder if the app is frozen. You need to stream partial results (which file is being written, how many tokens generated, etc.) from the backend to the frontend without WebSocket complexity.

## Pattern

Use **Server-Sent Events (SSE)** with an **async queue per request** as the bridge between the generation task and the HTTP response.

```
┌──────────┐     ┌───────────────┐     ┌──────────────┐
│ LLM Agent│────>│ Async Queue   │────>│ SSE Response │
│          │     │ (per request) │     │              │
│ partial  │     │               │     │ data: {...}  │
│ outputs  │     │ push_event()  │     │ data: {...}  │
│          │     │               │     │ data: {...}  │
└──────────┘     └───────────────┘     └──────────────┘
       │                                       │
       │         ┌──────────────┐              │
       └────────>│ Final Result │              │
                 │ (returned)   │              │
                 └──────────────┘              │
                                               ▼
                                        ┌──────────┐
                                        │ Frontend │
                                        │ EventSrc │
                                        └──────────┘
```

### Why SSE, Not WebSockets

- SSE is HTTP. No upgrade negotiation, no special proxy config, no reconnection protocol to implement.
- SSE is unidirectional (server to client) — which is exactly what streaming generation needs.
- SSE works through load balancers, CDNs, and reverse proxies with minimal config.
- The browser's `EventSource` API handles reconnection automatically.

### The Queue Layer

Each active generation gets its own `asyncio.Queue`. The generation task pushes events; the SSE endpoint consumes them.

```python
import asyncio
import json
from typing import AsyncGenerator, Dict, Any

# Global registry of active generation queues
_queues: Dict[str, asyncio.Queue] = {}


async def get_or_create_queue(request_id: str) -> asyncio.Queue:
    if request_id not in _queues:
        _queues[request_id] = asyncio.Queue()
    return _queues[request_id]


def remove_queue(request_id: str) -> None:
    _queues.pop(request_id, None)


async def push_event(request_id: str, event: Dict[str, Any]) -> None:
    if request_id in _queues:
        await _queues[request_id].put(event)
```

### The SSE Generator

Reads from the queue with a timeout. Sends keepalives to prevent connection drops. Stops on terminal events.

```python
async def sse_generator(
    request_id: str,
    timeout: float = 30.0,
) -> AsyncGenerator[str, None]:
    queue = await get_or_create_queue(request_id)

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=timeout)
                yield f"data: {json.dumps(event)}\n\n"

                # Stop on terminal events
                if event.get("type") in ("complete", "error"):
                    break
            except asyncio.TimeoutError:
                # Keepalive prevents proxy/browser timeout
                yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    finally:
        remove_queue(request_id)
```

### The SSE Response (FastAPI)

```python
from fastapi.responses import StreamingResponse

def create_sse_response(generator: AsyncGenerator[str, None]) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Prevents nginx buffering
        },
    )
```

### The Progress Callback

A typed callback class that the generation service calls. Translates generation events into queue events.

```python
class StreamingProgressCallback:
    def __init__(self, request_id: str):
        self.request_id = request_id

    async def on_progress(self, event_type: str, data: dict) -> None:
        await push_event(self.request_id, {"type": event_type, **data})

    async def thinking(self, message: str) -> None:
        await self.on_progress("thinking", {"message": message})

    async def generating(self, tokens: int, file_name: str | None = None,
                         content_tail: str | None = None) -> None:
        data = {"tokens": tokens}
        if file_name:
            data["file"] = file_name
        if content_tail:
            data["content_tail"] = content_tail[-100:]  # Last 100 chars only
        await self.on_progress("generating", data)

    async def complete(self, files: list, usage: dict | None = None) -> None:
        data = {"files": files}
        if usage:
            data["usage"] = usage
        await self.on_progress("complete", data)

    async def error(self, message: str) -> None:
        await self.on_progress("error", {"message": message})
```

### Wiring It Together (Generation Side)

The generation service accepts an optional callback and calls it during streaming:

```python
async def generate_streaming(self, prompt: str, on_progress=None, throttle_ms=100):
    last_update = 0
    tokens = 0

    async with self._agent.run_stream(prompt) as result:
        async for partial, is_last in result.stream_structured(debounce_by=throttle_ms / 1000):
            tokens += 1
            now = time.time() * 1000

            if on_progress and (now - last_update >= throttle_ms or is_last):
                last_update = now
                file_name = None
                content_tail = None

                if hasattr(partial, 'files') and partial.files:
                    last_file = partial.files[-1]
                    file_name = getattr(last_file, 'path', None)
                    content = getattr(last_file, 'content', '')
                    content_tail = content[-150:] if content else None

                await on_progress(StreamingUpdate(
                    type='partial_file' if file_name else 'generating',
                    tokens_so_far=tokens,
                    file_name=file_name,
                    partial_content=content_tail,
                ))

        final = await result.get_output()
        return final
```

### Wiring It Together (API Side)

```python
@router.get("/projects/{project_id}/generate/stream")
async def stream_generation(project_id: str):
    request_id = f"{project_id}_{secrets.token_urlsafe(4)}"

    # Start generation in background
    callback = StreamingProgressCallback(request_id)
    asyncio.create_task(
        run_generation(project_id, callback)
    )

    # Return SSE stream immediately
    return create_sse_response(sse_generator(request_id))
```

### Frontend (EventSource)

```typescript
function streamGeneration(projectId: string, onEvent: (event: any) => void) {
  const source = new EventSource(`/api/projects/${projectId}/generate/stream`);

  source.onmessage = (e) => {
    const event = JSON.parse(e.data);

    switch (event.type) {
      case 'thinking':
        onEvent({ status: 'thinking', message: event.message });
        break;
      case 'generating':
      case 'partial_file':
        onEvent({
          status: 'generating',
          tokens: event.tokens,
          currentFile: event.file,
          preview: event.content_tail,
        });
        break;
      case 'complete':
        onEvent({ status: 'complete', files: event.files });
        source.close();
        break;
      case 'error':
        onEvent({ status: 'error', message: event.message });
        source.close();
        break;
      case 'keepalive':
        break; // Ignore
    }
  };

  source.onerror = () => {
    onEvent({ status: 'error', message: 'Connection lost' });
    source.close();
  };

  return () => source.close(); // Cleanup function
}
```

## Event Protocol

Define a clear set of event types:

| Event | When | Payload |
|---|---|---|
| `thinking` | Agent is planning | `{message}` |
| `generating` | Tokens being produced | `{tokens, file?, content_tail?}` |
| `partial_file` | A file is being written | `{tokens, file, content_tail, files_complete}` |
| `complete` | Generation finished | `{files[], usage?}` |
| `error` | Something failed | `{message}` |
| `keepalive` | Heartbeat (no progress) | `{}` |

## Pitfalls

1. **No keepalive**: Proxies (nginx, AWS ALB) have idle timeouts (60s default). If the LLM is thinking for 45 seconds without output, the proxy kills the connection. Send keepalives every 30s.

2. **No debouncing**: Pydantic AI's `stream_structured` can fire hundreds of times per second. Without throttling, you flood the browser and the network. 100ms debounce is a good default.

3. **Forgetting queue cleanup**: If the client disconnects mid-stream, the queue stays in memory forever. The `finally` block in `sse_generator` handles this. Also consider a TTL-based cleanup for orphaned queues.

4. **Sending full content in events**: Streaming the entire file content in every event is wasteful. Send only the last 100-150 chars (`content_tail`) so the UI can show a "typing" effect.

5. **No terminal event**: If the generator crashes without pushing an `error` event, the SSE stream hangs until the keepalive timeout. Wrap your generation task in try/except and always push a terminal event.

6. **`X-Accel-Buffering: no`**: Without this header, nginx buffers the entire SSE stream and delivers it all at once when the connection closes. This defeats the purpose of streaming.

## When NOT to Use This Pattern

- **Sub-2-second operations**: If your LLM call reliably finishes in under 2 seconds, a normal request/response is simpler.
- **Bidirectional communication**: If the client needs to send messages during generation (cancel, modify prompt), use WebSockets instead.
- **Multiple concurrent consumers**: SSE is 1:1 (one generator, one consumer). If multiple clients need the same stream, add a pub/sub layer.

## Adapting This Pattern

| If you're using... | Replace... |
|---|---|
| Django instead of FastAPI | Use `StreamingHttpResponse` with `content_type="text/event-stream"`. The queue pattern stays the same. |
| WebSockets | Replace `sse_generator` with a WebSocket handler that reads from the same queue. The callback and queue layers don't change. |
| Redis pub/sub (multi-instance) | Replace the in-memory `_queues` dict with Redis pub/sub channels. Same push/consume pattern, works across processes. |
| A non-streaming LLM | Fake the stream with periodic "thinking" events, then send a single "complete" event. The frontend code doesn't change. |
