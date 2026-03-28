from fastapi import APIRouter, Request

from backend.apps.system.schemas import BackendRootResponse
from backend.apps.system.service import SystemService
from backend.logger import logger


router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/backend-root", response_model=BackendRootResponse)
def get_backend_root(request: Request) -> BackendRootResponse:
    endpoint_name = "system_backend_root"
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info("[%s] starting list backend root request_id=%s", endpoint_name, request_id)
    response = SystemService().backend_root_listing()
    logger.info(
        "[%s] completed list backend root request_id=%s entry_count=%s",
        endpoint_name,
        request_id,
        len(response.entries),
    )
    return response
