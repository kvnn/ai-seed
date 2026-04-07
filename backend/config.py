import os
from dataclasses import dataclass
from typing import List


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    backend_host: str
    api_host_port: int
    cors_origins: List[str]
    output_dir: str
    db_engine_url: str
    invite_code: str | None
    app_password: str | None
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_hours: int
    bootstrap_db: bool


settings = Settings(
    backend_host=os.getenv("BACKEND_HOST", "0.0.0.0"),
    api_host_port=int(os.getenv("API_HOST_PORT", "8000")),
    cors_origins=_split_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5176,http://localhost:3000")),
    output_dir=os.getenv("OUTPUT_DIR", "./data"),
    db_engine_url=os.getenv("DB_ENGINE_URL", "sqlite:///./data/oahuai.db"),
    invite_code=os.getenv("INVITE_CODE"),
    app_password=os.getenv("APP_PASSWORD"),
    jwt_secret=os.getenv("JWT_SECRET", os.getenv("APP_PASSWORD", "change-me")),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "24")),
    bootstrap_db=_get_bool("BOOTSTRAP_DB", True),
)
