from app.models.company import CompanyProfile
from app.models.compliance import ComplianceResult
from app.prompts.compliance import COMPLIANCE_SYSTEM_PROMPT, build_compliance_prompt
from app.services.llm import OpenRouterLLMService


class ComplianceService:
    def __init__(self, llm: OpenRouterLLMService) -> None:
        self.llm = llm

    async def screen(
        self,
        profile: CompanyProfile,
        competitor_candidates: list[str],
        restricted_jurisdictions: list[str],
    ) -> ComplianceResult:
        normalized_company = _normalize_company_name(profile.company)
        annotated_candidates = [
            f"{candidate} (normalized-name similarity: {SequenceMatcher(None, normalized_company, _normalize_company_name(candidate)).ratio():.2f})"
            for candidate in competitor_candidates
        ]
        return await self.llm.generate_structured(
            messages=[
                {"role": "system", "content": COMPLIANCE_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_compliance_prompt(
                        profile.model_dump_json(),
                        annotated_candidates,
                        restricted_jurisdictions,
                    ),
                },
            ],
            response_model=ComplianceResult,
            purpose="compliance_screening",
        )


def _normalize_company_name(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", value.lower())
    suffixes = {"inc", "incorporated", "llc", "ltd", "limited", "co", "company", "corp", "corporation"}
    return "".join(word for word in words if word not in suffixes)
import re
from difflib import SequenceMatcher

