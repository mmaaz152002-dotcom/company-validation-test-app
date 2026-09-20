from email_validator import EmailNotValidError, validate_email

FREE_EMAIL_DOMAINS = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com",
    "proton.me", "protonmail.com", "aol.com",
}


def registrable_domain(value: str) -> str:
    host = value.lower().strip().strip(".")
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    # Common multi-label public suffixes used in this prototype. The comparison
    # remains conservative for unfamiliar suffixes rather than accepting a TLD match.
    compound_suffixes = {"co.uk", "com.au", "co.nz", "co.jp", "com.br", "co.in"}
    suffix = ".".join(parts[-2:])
    return ".".join(parts[-3:]) if suffix in compound_suffixes else ".".join(parts[-2:])


def assess_email_alignment(email: str, website_domain: str) -> str:
    try:
        normalized = validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError:
        return "invalid"
    email_domain = normalized.rsplit("@", 1)[1].lower()
    if email_domain in FREE_EMAIL_DOMAINS:
        return "free_email_provider"
    if registrable_domain(email_domain) == registrable_domain(website_domain):
        return "company_domain_match"
    return "domain_mismatch"

