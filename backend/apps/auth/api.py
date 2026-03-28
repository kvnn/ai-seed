from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.apps.auth.schemas import (
    AuthResponse,
    BootstrapRequest,
    CreateInviteRequest,
    InviteCodeResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)
from backend.apps.auth.service import AuthService, create_bootstrap_admin, decode_token
from backend.database import get_db


router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[dict]:
    token_str = credentials.credentials if credentials else None
    if not token_str:
        return None
    payload = decode_token(token_str)
    if not payload:
        return None
    return AuthService(db).get_user(payload.get("sub", ""))


def require_user(user: Optional[dict] = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="not_authenticated")
    return user


def require_admin(user: dict = Depends(require_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="admin_required")
    return user


@router.post("/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    service = AuthService(db)
    try:
        return AuthResponse(**service.register(
            email=payload.email,
            password=payload.password,
            invite_code=payload.invite_code,
            name=payload.name,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    service = AuthService(db)
    try:
        return AuthResponse(**service.login(email=payload.email, password=payload.password))
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(require_user)) -> UserResponse:
    return UserResponse(**user)


@router.post("/invite", response_model=InviteCodeResponse)
def create_invite(
    payload: CreateInviteRequest,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> InviteCodeResponse:
    service = AuthService(db)
    code = service.create_invite_code(
        created_by=user["id"],
        max_uses=payload.max_uses,
        expires_in_days=payload.expires_in_days,
    )
    return InviteCodeResponse.model_validate(code, from_attributes=True)


@router.get("/invites", response_model=list[InviteCodeResponse])
def list_invites(
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[InviteCodeResponse]:
    service = AuthService(db)
    if user.get("is_admin"):
        invites = service.list_invite_codes()
    else:
        invites = service.list_invite_codes(created_by=user["id"])
    return [InviteCodeResponse.model_validate(invite, from_attributes=True) for invite in invites]


@router.delete("/invites/{code_id}")
def delete_invite(
    code_id: int,
    user: dict = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    service = AuthService(db)
    user_id = None if user.get("is_admin") else user["id"]
    deleted = service.delete_invite_code(code_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="invite_not_found")
    return {"deleted": True}


@router.post("/bootstrap", response_model=AuthResponse)
def bootstrap(payload: BootstrapRequest, db: Session = Depends(get_db)) -> AuthResponse:
    try:
        return AuthResponse(**create_bootstrap_admin(db, payload.email, payload.password))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
