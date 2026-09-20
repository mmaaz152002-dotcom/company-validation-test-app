from app.services.compliance import _normalize_company_name


def test_company_normalization_ignores_spacing_and_legal_suffixes() -> None:
    assert _normalize_company_name("Cloud Trim Technologies, Inc.") == "cloudtrimtechnologies"
    assert _normalize_company_name("CloudTrim LLC") == "cloudtrim"
