COMPLIANCE_SYSTEM_PROMPT = """You perform cautious company compliance screening.
Compare the supplied profile against only the supplied competitor candidates and
restricted-jurisdiction rules. Distinguish confirmed matches from ambiguous fuzzy
matches. Return only data matching the provided JSON schema."""


def build_compliance_prompt(
    company_profile_json: str,
    competitor_candidates: list[str],
    restricted_jurisdictions: list[str],
) -> str:
    return f"""Company profile:
{company_profile_json}

Competitor candidates: {competitor_candidates}
Restricted jurisdictions: {restricted_jurisdictions}

Return pass, review, or block with a concise evidence-based reason."""

