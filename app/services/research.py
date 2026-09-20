from urllib.parse import urlsplit

from app.models.company import CompanyProfile
from app.prompts.research import RESEARCH_SYSTEM_PROMPT, build_research_prompt
from app.services.llm import OpenRouterLLMService


def normalize_domain(value: str) -> str:
    candidate = value.strip().lower()
    parsed = urlsplit(candidate if "://" in candidate else f"//{candidate}")
    host = (parsed.hostname or "").removeprefix("www.").rstrip(".")
    if not host or "." not in host:
        raise ValueError("A valid company domain is required.")
    return host


class CompanyResearchService:
    def __init__(self, llm: OpenRouterLLMService) -> None:
        self.llm = llm
        self._cache: dict[str, CompanyProfile] = {}

    async def research(self, domain: str, public_evidence: str) -> CompanyProfile:
        normalized = normalize_domain(domain)
        if normalized in self._cache:
            return self._cache[normalized]

        profile = await self.llm.generate_structured(
            messages=[
                {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_research_prompt(normalized, public_evidence),
                },
            ],
            response_model=CompanyProfile,
            purpose="company_research",
        )
        # The cache key, not model prose, controls identity and reuse.
        profile = profile.model_copy(update={"domain": normalized})
        self._cache[normalized] = profile
        return profile

