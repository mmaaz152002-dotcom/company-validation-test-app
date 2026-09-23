from dataclasses import dataclass

import phonenumbers
from phonenumbers import geocoder

from app.services.policy import CountryRule


class PhoneValidationError(ValueError):
    pass


@dataclass(frozen=True)
class PhoneAssessment:
    e164: str
    country_code: str
    country_name: str
    dial_code: str
    risk: str
    risk_reason: str


def assess_phone_number(
    raw_number: str,
    selected_country: str | None,
    country_rules: dict[str, CountryRule],
) -> PhoneAssessment:
    value = raw_number.strip()
    region = (selected_country or "").strip().upper() or None
    if not value:
        raise PhoneValidationError("Phone number is required.")
    if not value.startswith("+") and not region:
        raise PhoneValidationError(
            "Choose a country or enter the phone number in international format starting with +."
        )
    try:
        parsed = phonenumbers.parse(value, None if value.startswith("+") else region)
    except phonenumbers.NumberParseException as exc:
        raise PhoneValidationError("The phone number format is not valid.") from exc
    if not phonenumbers.is_possible_number(parsed):
        raise PhoneValidationError("The phone number has an impossible length or format.")
    if not phonenumbers.is_valid_number(parsed):
        raise PhoneValidationError("The phone number is not valid for the detected country.")
    detected = phonenumbers.region_code_for_number(parsed)
    if not detected:
        raise PhoneValidationError("A country could not be detected from this phone number.")
    rule = country_rules.get(detected)
    return PhoneAssessment(
        e164=phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        country_code=detected,
        country_name=geocoder.description_for_number(parsed, "en") or detected,
        dial_code=f"+{parsed.country_code}",
        risk=rule.risk if rule else "standard",
        risk_reason=rule.reason if rule else "No configured country restriction.",
    )


def supported_calling_codes() -> list[dict[str, str]]:
    options = []
    for region in sorted(phonenumbers.SUPPORTED_REGIONS):
        code = phonenumbers.country_code_for_region(region)
        if code:
            options.append({"country_code": region, "dial_code": f"+{code}"})
    return options

