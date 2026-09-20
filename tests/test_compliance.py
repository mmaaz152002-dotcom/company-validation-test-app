from app.services.basic_screening import basic_compliance_screen, normalize_company_name


def test_company_normalization_ignores_spacing_and_legal_suffixes() -> None:
    assert normalize_company_name("Cloud Trim Technologies, Inc.") == "cloudtrimtechnologies"
    assert normalize_company_name("CloudTrim LLC") == "cloudtrim"


def test_basic_screen_blocks_exact_competitor_name_without_research() -> None:
    result = basic_compliance_screen("Cloud Trim LLC", "unreachable.example")
    assert result is not None
    assert result.status == "block"
    assert result.confidence == 1.0


def test_basic_screen_blocks_known_competitor_domain() -> None:
    result = basic_compliance_screen("Different Display Name", "cloudtrim.ai")
    assert result is not None
    assert result.status == "block"


def test_basic_screen_allows_unknown_company_to_continue() -> None:
    assert basic_compliance_screen("Acme Industries", "acme.example") is None
