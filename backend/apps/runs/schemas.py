from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


RunStatus = Literal["draft", "research_ready", "brand_ready", "site_ready", "approved", "published", "failed"]
RunStage = Literal["research", "brand", "site"]


class ResearchArtifact(BaseModel):
    summary: str
    source_label: str
    recommended_audience: str
    key_facts: list[str] = Field(default_factory=list)
    cautions: list[str] = Field(default_factory=list)


class BrandArtifact(BaseModel):
    vision: str
    value: str
    voice: str
    brand_imagery: list[str] = Field(default_factory=list)
    color_palette_hex: list[str] = Field(default_factory=list)


class GeneratedFile(BaseModel):
    path: str
    media_type: Optional[str] = None
    content: str


class SiteArtifact(BaseModel):
    title: str
    description: str
    entrypoint: str = "index.html"
    files: list[GeneratedFile] = Field(default_factory=list)


class RunCreateRequest(BaseModel):
    brief: str = Field(min_length=12)
    source_url: Optional[HttpUrl] = None
    preferred_style: Optional[str] = None
    publish_slug: Optional[str] = None
    required_facts: list[str] = Field(default_factory=list)
    banned_claims: list[str] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=1000)


class RetryRequest(BaseModel):
    stage: Optional[RunStage] = None


class RunResponse(BaseModel):
    id: str
    status: RunStatus
    source_url: Optional[str] = None
    brief: str
    preferred_style: Optional[str] = None
    publish_slug: str
    required_facts: list[str] = Field(default_factory=list)
    banned_claims: list[str] = Field(default_factory=list)
    research: Optional[ResearchArtifact] = None
    brand: Optional[BrandArtifact] = None
    site: Optional[SiteArtifact] = None
    next_actions: list[str] = Field(default_factory=list)
    preview_url: Optional[str] = None
    published_path: Optional[str] = None
    failed_stage: Optional[RunStage] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None


class RunListResponse(BaseModel):
    runs: list[RunResponse] = Field(default_factory=list)
