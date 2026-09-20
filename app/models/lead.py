from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl

from app.models.company import CompanyProfile
from app.models.compliance import ComplianceResult


class LeadSubmission(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    company_name: str = Field(min_length=2, max_length=200)
    website: HttpUrl
    job_title: str | None = Field(default=None, max_length=120)
    # Optional in the stored schema for backward compatibility with earlier rows;
    # the current browser form requires it before submission.
    notification_email: EmailStr | None = None


class FitBreakdown(BaseModel):
    company_size: int = Field(ge=0, le=35)
    cloud_intensity: int = Field(ge=0, le=40)
    business_model: int = Field(ge=0, le=15)
    lead_quality: int = Field(ge=0, le=10)


class FitResult(BaseModel):
    score: int = Field(ge=0, le=100)
    category: Literal["low", "borderline", "promising", "strong"]
    breakdown: FitBreakdown
    reasons: list[str]


class LeadResult(BaseModel):
    id: int
    created_at: datetime
    lead: LeadSubmission
    email_alignment: str
    profile: CompanyProfile
    fit: FitResult
    compliance: ComplianceResult
    disposition: Literal["sales_ready", "manual_review", "blocked"]
    notification_status: Literal["sent", "failed", "skipped"]
