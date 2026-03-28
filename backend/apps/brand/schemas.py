from typing import Optional

from pydantic import BaseModel, Field


class ExtractedBrandKit(BaseModel):
    vision: Optional[str] = Field(default=None, description="Vision statement")
    brand_imagery: list[str] = Field(default_factory=list, description="Visual style descriptors")
    color_palette_hex: list[str] = Field(default_factory=list, description="Color palette as hex codes")
    meaning: Optional[str] = None
    authenticity: Optional[str] = None
    coherence: Optional[str] = None
    differentiation: Optional[str] = None
    flexibility: Optional[str] = None
    sustainability: Optional[str] = None
    commitment: Optional[str] = None
    value: Optional[str] = None


class GeneratedBrandContent(BaseModel):
    vision: str = Field(description="A compelling vision statement in one or two sentences")
    meaning: Optional[str] = Field(default=None, description="What the brand stands for")
    value: str = Field(description="Value proposition in one or two sentences")
    differentiation: Optional[str] = Field(default=None, description="What makes this brand unique")

