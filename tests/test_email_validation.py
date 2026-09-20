from app.services.email_validation import assess_email_alignment, registrable_domain


def test_company_subdomain_email_matches_website() -> None:
    assert registrable_domain("team.acme.co.uk") == "acme.co.uk"
    assert assess_email_alignment("jane@team.acme.co.uk", "www.acme.co.uk") == "company_domain_match"


def test_free_email_is_not_treated_as_company_email() -> None:
    assert assess_email_alignment("founder@gmail.com", "company.com") == "free_email_provider"

