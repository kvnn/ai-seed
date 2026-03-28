import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.logger import logger
from backend.models import InviteCode, User


def _short_id() -> str:
    return secrets.token_urlsafe(6)[:8]


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "***"
    return f"{masked_local}@{domain}"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(
    user_id: str,
    email: str,
    is_admin: bool = False,
    extra_claims: Optional[dict] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": user_id,
        "email": email,
        "is_admin": is_admin,
        "exp": expire,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        logger.debug("[auth] token decode failed error=%s", str(exc))
        return None


def _user_response(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "is_admin": user.is_admin,
        "created_at": user.created_at,
    }


class AuthService:
    def __init__(self, session: Session):
        self._session = session

    def _get_user_by_email(self, email: str) -> Optional[User]:
        stmt: Select[tuple[User]] = select(User).where(User.email == email)
        return self._session.execute(stmt).scalar_one_or_none()

    def register(
        self,
        email: str,
        password: str,
        invite_code: str,
        name: Optional[str] = None,
    ) -> dict:
        email = email.lower().strip()
        if self._get_user_by_email(email):
            raise ValueError("email_already_exists")

        universal_code = settings.invite_code
        use_universal = bool(universal_code and invite_code == universal_code)
        code = None

        if not use_universal:
            code = self._session.execute(
                select(InviteCode).where(InviteCode.code == invite_code)
            ).scalar_one_or_none()
            if not code:
                raise ValueError("invalid_invite_code")
            if code.max_uses > 0 and code.use_count >= code.max_uses:
                raise ValueError("invite_code_exhausted")
            if code.expires_at and code.expires_at < datetime.now(timezone.utc):
                raise ValueError("invite_code_expired")

        user = User(
            id=_short_id(),
            email=email,
            password_hash=hash_password(password),
            name=name,
            is_admin=False,
        )
        self._session.add(user)

        if code:
            code.use_count += 1
            code.used_by = user.id

        self._session.commit()
        self._session.refresh(user)

        logger.info(
            "[auth] register_success user_id=%s email=%s universal_invite=%s",
            user.id,
            _mask_email(user.email),
            use_universal,
        )

        token = create_access_token(user.id, user.email, user.is_admin)
        return {"user": _user_response(user), "access_token": token, "token_type": "bearer"}

    def login(self, email: str, password: str) -> dict:
        email = email.lower().strip()
        user = self._get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("invalid_credentials")

        logger.info("[auth] login_success user_id=%s email=%s", user.id, _mask_email(user.email))

        token = create_access_token(user.id, user.email, user.is_admin)
        return {"user": _user_response(user), "access_token": token, "token_type": "bearer"}

    def get_user(self, user_id: str) -> Optional[dict]:
        user = self._session.get(User, user_id)
        if not user:
            return None
        return _user_response(user)

    def create_invite_code(
        self,
        created_by: Optional[str] = None,
        max_uses: int = 1,
        expires_in_days: Optional[int] = None,
    ) -> InviteCode:
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        invite = InviteCode(
            code=secrets.token_urlsafe(8),
            created_by=created_by,
            max_uses=max_uses,
            expires_at=expires_at,
        )
        self._session.add(invite)
        self._session.commit()
        self._session.refresh(invite)

        logger.info("[auth] invite_created invite_id=%s created_by=%s", invite.id, created_by)
        return invite

    def list_invite_codes(self, created_by: Optional[str] = None) -> list[InviteCode]:
        stmt = select(InviteCode).order_by(InviteCode.created_at.desc())
        if created_by:
            stmt = stmt.where(InviteCode.created_by == created_by)
        return list(self._session.execute(stmt).scalars().all())

    def delete_invite_code(self, code_id: int, user_id: Optional[str] = None) -> bool:
        code = self._session.get(InviteCode, code_id)
        if not code:
            return False
        if user_id and code.created_by != user_id:
            return False
        self._session.delete(code)
        self._session.commit()
        logger.info("[auth] invite_deleted invite_id=%s actor_user_id=%s", code_id, user_id)
        return True


def create_bootstrap_admin(session: Session, email: str, password: str) -> dict:
    existing_user = session.execute(select(User).limit(1)).scalar_one_or_none()
    if existing_user:
        raise ValueError("users_already_exist")

    user = User(
        id=_short_id(),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        name="Admin",
        is_admin=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info("[auth] bootstrap_admin_created user_id=%s email=%s", user.id, _mask_email(user.email))

    token = create_access_token(user.id, user.email, user.is_admin)
    return {"user": _user_response(user), "access_token": token, "token_type": "bearer"}
