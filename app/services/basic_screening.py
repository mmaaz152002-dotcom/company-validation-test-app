import re
from dataclasses import dataclass

from app.models.compliance import ComplianceResult, ComplianceStatus


@dataclass(frozen=True)
class CompetitorRule:
    name: str
    aliases: tuple[str, ...] = ()
    domains: tuple[str, ...] = ()


KNOWN_COMPETITORS = (
    CompetitorRule(
        name="CloudTrim Inc",
        aliases=("CloudTrim", "Cloud Trim"),
        domains=("cloudtrim.ai", "cloudtrim.cloud"),
    ),
    CompetitorRule(name="SpendWise Cloud", aliases=("Spend Wise Cloud",)),
    CompetitorRule(name="RightSize Cloud Co", aliases=("Right Size Cloud",)),
)


def normalize_company_name(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", value.lower())
    suffixes = {
        "inc", "incorporated", "llc", "ltd", "limited", "co", "company",
        "corp", "corporation",
    }
    return "".join(word for word in words if word not in suffixes)


def basic_compliance_screen(company_name: str, domain: str) -> ComplianceResult | None:
    normalized_name = normalize_company_name(company_name)
    normalized_domain = domain.lower().removeprefix("www.").rstrip(".")
    for competitor in KNOWN_COMPETITORS:
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

