import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.apps.auth.api import router as auth_router
from backend.apps.runs.api import preview_router, router as runs_router
from backend.apps.system.api import router as system_router
from backend.config import settings
from backend.database import init_db
from backend.logger import logger


app = FastAPI(title="OahuAI Seed API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    logger.info("[startup] completed database initialization bootstrap_db=%s", settings.bootstrap_db)


@app.middleware("http")
async def api_logging_middleware(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    endpoint_name = request.url.path
    request.state.request_id = request_id
    start = time.perf_counter()

    logger.info(
        "[api] starting endpoint_name=%s request_id=%s",
        endpoint_name,
        request_id,
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception(
            "[api] error endpoint_name=%s request_id=%s duration_ms=%s status_code=%s error=%s",
            endpoint_name,
            request_id,
            duration_ms,
            500,
            str(exc),
        )
        return JSONResponse(status_code=500, content={"detail": "internal_server_error", "request_id": request_id})

    duration_ms = int((time.perf_counter() - start) * 1000)
    if response.status_code >= 400:
        logger.error(
            "[api] error endpoint_name=%s request_id=%s duration_ms=%s status_code=%s",
            endpoint_name,
            request_id,
            duration_ms,
            response.status_code,
        )
    else:
        logger.info(
            "[api] completed endpoint_name=%s request_id=%s duration_ms=%s status_code=%s",
            endpoint_name,
            request_id,
            duration_ms,
            response.status_code,
        )
    return response


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(runs_router)
app.include_router(preview_router)
app.include_router(system_router)
