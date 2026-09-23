import re

from app.models.compliance import ComplianceResult, ComplianceStatus
from app.services.phone_validation import PhoneAssessment
from app.services.policy import CompetitorRule


def normalize_company_name(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", value.lower())
    suffixes = {
        "inc", "incorporated", "llc", "ltd", "limited", "co", "company",
        "corp", "corporation",
    }
    return "".join(word for word in words if word not in suffixes)


def basic_compliance_screen(
    company_name: str,
    domain: str,
    competitors: tuple[CompetitorRule, ...],
    phone: PhoneAssessment,
) -> ComplianceResult | None:
    if phone.risk == "blocked":
        return ComplianceResult(
            status=ComplianceStatus.BLOCK,
            matched_rule=f"Blocked phone country: {phone.country_name} ({phone.country_code})",
            confidence=1.0,
            reason=(
                f"Blocked during basic screening because the validated phone number belongs "
                f"to {phone.country_name}. {phone.risk_reason} Website research and LLM "
                "screening were skipped."
            ),
        )
    normalized_name = normalize_company_name(company_name)
    normalized_domain = domain.lower().removeprefix("www.").rstrip(".")
    for competitor in competitors:
        known_names = (competitor.name, *competitor.aliases)
        name_match = normalized_name in {
            normalize_company_name(value) for value in known_names
        }
        domain_match = normalized_domain in competitor.domains
        if not name_match and not domain_match:
            continue
        matched_by = []
        if name_match:
            matched_by.append("submitted company name")
        if domain_match:
            matched_by.append("submitted website domain")
        return ComplianceResult(
            status=ComplianceStatus.BLOCK,
            matched_rule=f"Known competitor: {competitor.name}",
            confidence=1.0,
            reason=(
                f"Blocked during basic screening because {' and '.join(matched_by)} "
                f"matched the configured competitor record for {competitor.name}. "
                "Website research and LLM screening were skipped."
            ),
        )
    return None
