from datetime import datetime, timezone
from pathlib import Path

from backend.apps.system.schemas import BackendRootEntryResponse, BackendRootResponse


def _backend_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _entry_kind(path: Path) -> str:
    if path.is_dir():
        return "dir"
    if path.is_file():
        return "file"
    return "other"


class SystemService:
    def backend_root_listing(self) -> BackendRootResponse:
        root = _backend_root()
        entries = sorted(
            (BackendRootEntryResponse(name=entry.name, kind=_entry_kind(entry)) for entry in root.iterdir()),
            key=lambda entry: (entry.kind != "dir", entry.name.lower()),
        )
        return BackendRootResponse(
            root_name=root.name,
            generated_at=datetime.now(timezone.utc),
            entries=entries,
        )
