from app.models.company import CompanyProfile
from app.models.lead import FitBreakdown, FitResult


def calculate_fit(profile: CompanyProfile, email_alignment: str) -> FitResult:
    reasons: list[str] = []
    employees = profile.employee_estimate
    if employees is None:
        size_points = {"micro": 3, "small": 10, "medium": 22, "large": 30, "enterprise": 35}.get(profile.size_band, 5)
    elif employees >= 1000:
        size_points = 35
    elif employees >= 201:
        size_points = 30
    elif employees >= 51:
        size_points = 22
    elif employees >= 11:
        size_points = 10
    else:
        size_points = 3
    reasons.append(f"Company size contributes {size_points}/35.")

    cloud_points = {"high": 40, "medium": 25, "low": 8, "unknown": 5}[profile.cloud_intensity]
    signal_bonus = min(5, len(profile.cloud_signals))
    cloud_points = min(40, cloud_points + signal_bonus)
    reasons.append(f"Cloud intensity and {len(profile.cloud_signals)} signal(s) contribute {cloud_points}/40.")

    fit_terms = (profile.business_model + " " + " ".join(profile.products_services)).lower()
    if any(term in fit_terms for term in ("saas", "software", "platform", "cloud", "data", "marketplace")):
        business_points = 15
    elif any(term in fit_terms for term in ("digital", "technology", "online", "subscription")):
        business_points = 10
    else:
        business_points = 5
    reasons.append(f"Business model contributes {business_points}/15.")

    lead_points = {
        "company_domain_match": 10,
        "domain_mismatch": 4,
        "free_email_provider": 2,
        "invalid": 0,
    }.get(email_alignment, 3)
    reasons.append(f"Lead email quality contributes {lead_points}/10.")

    breakdown = FitBreakdown(
        company_size=size_points,
        cloud_intensity=cloud_points,
        business_model=business_points,
        lead_quality=lead_points,
    )
    score = sum(breakdown.model_dump().values())
    category = "strong" if score >= 75 else "promising" if score >= 50 else "borderline" if score >= 25 else "low"
    return FitResult(score=score, category=category, breakdown=breakdown, reasons=reasons)

