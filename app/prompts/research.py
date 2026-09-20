RESEARCH_SYSTEM_PROMPT = """You create one evidence-grounded company profile.
Use only the supplied website/public evidence. Do not invent facts. When evidence is
insufficient, use null, an empty list, or \"unknown\" as allowed by the schema.
Return only data matching the provided JSON schema. Source entries must explain which
claim each URL supports."""


def build_research_prompt(domain: str, evidence: str) -> str:
    return f"""Research the company associated with normalized domain: {domain}

Public evidence:
{evidence}

Create the complete company profile in one response."""

