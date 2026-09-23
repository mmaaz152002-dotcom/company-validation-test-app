from app.models.compliance import ComplianceResult
from app.services.disposition import decide_disposition


def compliance(status: str, reason: str = "No restricted match found") -> ComplianceResult:
    return ComplianceResult(status=status, confidence=0.9, reason=reason)


def test_blocked_disposition_explains_compliance_rule() -> None:
    disposition, reasons = decide_disposition(
        compliance("block", "Likely competitor match"), 90, "standard", "Allowed", "company_match"
    )
    assert disposition == "blocked"
    assert reasons == ["Detailed compliance screening returned block: Likely competitor match"]


def test_manual_review_lists_every_trigger() -> None:
    disposition, reasons = decide_disposition(
        compliance("review", "Headquarters evidence is ambiguous"),
        42,
        "gray",
        "Enhanced review is required",
        "domain_mismatch",
    )
    assert disposition == "manual_review"
    assert len(reasons) == 4
    assert any("Compliance screening" in reason for reason in reasons)
    assert any("gray-area" in reason for reason in reasons)
    assert any("42/100" in reason for reason in reasons)
    assert any("does not match" in reason for reason in reasons)


def test_sales_ready_explains_that_all_gates_passed() -> None:
    disposition, reasons = decide_disposition(
        compliance("pass"), 75, "standard", "Allowed", "company_match"
    )
    assert disposition == "sales_ready"
    assert len(reasons) == 1
    assert "All routing gates passed" in reasons[0]
