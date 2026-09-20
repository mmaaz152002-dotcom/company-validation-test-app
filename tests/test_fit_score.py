from app.models.company import CompanyProfile
from app.services.fit_score import calculate_fit


def test_strong_cloud_company_score_is_explainable() -> None:
    profile = CompanyProfile(
        company="Scale Cloud",
        domain="scale.example",
        summary="Cloud software company",
        employee_estimate=800,
        business_model="B2B SaaS platform",
        products_services=["Cloud data platform"],
        cloud_signals=["AWS", "Kubernetes", "Terraform"],
        cloud_intensity="high",
        confidence=0.9,
    )
    result = calculate_fit(profile, "company_domain_match")
    assert result.score == 95
    assert result.category == "strong"
    assert result.breakdown.model_dump() == {
        "company_size": 30,
        "cloud_intensity": 40,
        "business_model": 15,
        "lead_quality": 10,
    }


def test_low_information_small_company_does_not_receive_high_score() -> None:
    profile = CompanyProfile(
        company="Local Shop",
        domain="shop.example",
        summary="Local retailer",
        employee_estimate=4,
        business_model="Retail",
        cloud_intensity="unknown",
        confidence=0.4,
    )
    result = calculate_fit(profile, "free_email_provider")
    assert result.score == 15
    assert result.category == "low"

