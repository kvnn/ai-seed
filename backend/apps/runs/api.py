import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.apps.auth.api import require_user
from backend.apps.runs.schemas import ApprovalRequest, RetryRequest, RunCreateRequest, RunListResponse, RunResponse
from backend.apps.runs.service import RunService
from backend.database import get_db


router = APIRouter(prefix="/api/runs", tags=["runs"])
preview_router = APIRouter(tags=["preview"])


@router.post("", response_model=RunResponse)
def create_run(
    payload: RunCreateRequest,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    return RunService(db).create_run(created_by=user["id"], payload=payload)


@router.get("", response_model=RunListResponse)
def list_runs(
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> RunListResponse:
    service = RunService(db)
    created_by = None if user.get("is_admin") else user["id"]
    return RunListResponse(runs=service.list_runs(created_by=created_by))


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    service = RunService(db)
    try:
        return service.get_run(run_id, created_by=user["id"], is_admin=user.get("is_admin", False))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{run_id}/approve", response_model=RunResponse)
def approve_run(
    run_id: str,
    payload: ApprovalRequest,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    service = RunService(db)
    try:
        return service.approve(run_id, actor_user_id=user["id"], payload=payload, is_admin=user.get("is_admin", False))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/retry", response_model=RunResponse)
def retry_run(
    run_id: str,
    payload: RetryRequest,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    service = RunService(db)
    try:
        return service.retry(run_id, actor_user_id=user["id"], payload=payload, is_admin=user.get("is_admin", False))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/publish", response_model=RunResponse)
def publish_run(
    run_id: str,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> RunResponse:
    service = RunService(db)
    try:
        return service.publish(run_id, actor_user_id=user["id"], is_admin=user.get("is_admin", False))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@preview_router.get("/preview/runs/{run_id}/site/{file_path:path}")
def preview_run_file(
    run_id: str,
    file_path: str,
    _: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    service = RunService(db)
    try:
        path = service.preview_file_path(run_id, file_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type)
