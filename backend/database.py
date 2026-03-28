from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import settings
from backend.logger import logger


class Base(DeclarativeBase):
    """Base declarative model."""


def _normalize_db_url(db_url: str) -> str:
    if db_url.startswith("postgresql+asyncpg://"):
        normalized = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        logger.info("[database] normalized async db url driver from asyncpg to psycopg for sync engine")
        return normalized
    return db_url


def _create_engine() -> Engine:
    db_url = _normalize_db_url(settings.db_engine_url)
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", "", 1))
        if not db_path.is_absolute():
            db_path = Path.cwd() / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(db_url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(db_url, future=True)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    if not settings.bootstrap_db:
        return
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
