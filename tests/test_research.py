import pytest

from app.models.company import CompanyProfile
from app.services.research import CompanyResearchService, normalize_domain


class FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_structured(self, **_: object) -> CompanyProfile:
        self.calls += 1
        return CompanyProfile(
            company="Acme",
            domain="model-output.example",
            summary="Example",
            business_model="B2B",
            cloud_intensity="unknown",
            confidence=0.5,
        )


def test_normalize_domain() -> None:
    assert normalize_domain("https://WWW.Example.com/path") == "example.com"


@pytest.mark.asyncio
async def test_company_research_is_cached_by_normalized_domain() -> None:
    llm = FakeLLM()
    service = CompanyResearchService(llm)  # type: ignore[arg-type]
    first = await service.research("https://www.acme.com/about", "evidence")
    second = await service.research("acme.com", "different evidence")
    assert first is second
    assert first.domain == "acme.com"
    assert llm.calls == 1
