from datetime import datetime
from typing import Literal

from pydantic import BaseModel


EntryKind = Literal["dir", "file", "other"]


class BackendRootEntryResponse(BaseModel):
    name: str
    kind: EntryKind


class BackendRootResponse(BaseModel):
    root_name: str
    generated_at: datetime
    entries: list[BackendRootEntryResponse]
