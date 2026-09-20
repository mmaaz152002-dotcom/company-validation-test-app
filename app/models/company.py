from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class Source(BaseModel):
    url: HttpUrl
    title: str = ""
    supports: str


class CompanyProfile(BaseModel):
    company: str
    domain: str
    summary: str
    headquarters: str | None = None
    employee_estimate: int | None = Field(default=None, ge=0)
    business_model: str
    products_services: list[str] = Field(default_factory=list)
    size_band: Literal["micro", "small", "medium", "large", "enterprise", "unknown"] = "unknown"
    cloud_signals: list[str] = Field(default_factory=list)
    cloud_intensity: Literal["low", "medium", "high", "unknown"]
    confidence: float = Field(ge=0, le=1)
    sources: list[Source] = Field(default_factory=list)
