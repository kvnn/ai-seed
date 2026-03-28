from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    invite_code: str
    name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ImpersonationSessionResponse(BaseModel):
    active: bool = True
    actor_user_id: str
    actor_email: EmailStr
    audit_id: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    is_admin: bool = False
    created_at: datetime
    impersonation: Optional[ImpersonationSessionResponse] = None


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"


class CreateInviteRequest(BaseModel):
    max_uses: int = Field(default=1, ge=0)
    expires_in_days: Optional[int] = Field(default=None, ge=1)


class InviteCodeResponse(BaseModel):
    id: int
    code: str
    max_uses: int
    use_count: int
    expires_at: Optional[datetime] = None
    created_at: datetime


class BootstrapRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
