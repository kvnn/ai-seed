from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class GeneratedFile(BaseModel):
    path: str = Field(description="Relative path inside the generated site, like index.html or assets/site.css")
    media_type: Optional[str] = Field(default=None, description="Optional mime type hint")
    content: str = Field(description="UTF-8 file content")


class GeneratedSite(BaseModel):
    title: str
    description: str
    entrypoint: str = Field(default="index.html")
    files: List[GeneratedFile] = Field(default_factory=list)


class GenerateSiteRequest(BaseModel):
    prompt: str
    source_url: Optional[str] = None
    preferred_style: Optional[str] = None
    formats_hint: Optional[List[str]] = None


class GenerateSiteResponse(BaseModel):
    run_id: str
    build_id: Optional[str] = None
    preview_url: str
    entrypoint: str
    files: List[str]
    title: str
    description: str
