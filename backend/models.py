from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    invite_codes: Mapped[list["InviteCode"]] = relationship(back_populates="creator")
    runs: Mapped[list["Run"]] = relationship(back_populates="creator")


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(16), ForeignKey("users.id"), nullable=True, index=True)
    used_by: Mapped[str | None] = mapped_column(String(16), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    use_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    creator: Mapped[User | None] = relationship(back_populates="invite_codes")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    created_by: Mapped[str | None] = mapped_column(String(16), ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    brief: Mapped[str] = mapped_column(Text)
    preferred_style: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_slug: Mapped[str] = mapped_column(String(255), index=True)
    required_facts: Mapped[list[str]] = mapped_column(JSON, default=list)
    banned_claims: Mapped[list[str]] = mapped_column(JSON, default=list)
    research_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    brand_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    site_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approval_history: Mapped[list[dict]] = mapped_column(JSON, default=list)
    failed_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creator: Mapped[User | None] = relationship(back_populates="runs")
