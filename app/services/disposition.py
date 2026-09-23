from app.models.compliance import ComplianceResult


def decide_disposition(
    compliance: ComplianceResult,
    fit_score: int,
    phone_risk: str,
    phone_risk_reason: str,
    email_alignment: str,
) -> tuple[str, list[str]]:
    """Return the sales routing decision and every deterministic trigger behind it."""
    if compliance.status == "block":
        return "blocked", [
            f"Detailed compliance screening returned block: {compliance.reason}"
        ]

    reasons: list[str] = []
    if compliance.status == "review":
        reasons.append(
            f"Compliance screening requires human review: {compliance.reason}"
        )
    if phone_risk == "gray":
        reasons.append(
            f"The validated phone country is in the gray-area policy: {phone_risk_reason}"
        )
    if fit_score < 50:
        reasons.append(
            f"The fit score is {fit_score}/100, below the 50-point sales-ready threshold."
        )
    if email_alignment == "domain_mismatch":
        reasons.append(
            "The submitted work-email domain does not match the company website domain."
        )
    elif email_alignment == "free_email_provider":
        reasons.append(
            "The submitted address uses a free email provider instead of the company domain."
        )

    if reasons:
        return "manual_review", reasons

    return "sales_ready", [
        f"All routing gates passed: compliance passed, fit score {fit_score}/100 met the "
        "50-point threshold, the phone country is standard risk, and the email-domain "
        "check passed."
    ]
