from enum import StrEnum

from pydantic import BaseModel, Field


class ComplianceStatus(StrEnum):
    PASS = "pass"
    REVIEW = "review"
    BLOCK = "block"


class ComplianceResult(BaseModel):
    status: ComplianceStatus
    matched_rule: str | None = None
    possible_match: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason: str

