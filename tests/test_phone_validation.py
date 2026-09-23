import pytest

from app.services.phone_validation import PhoneValidationError, assess_phone_number
from app.services.policy import CountryRule

RULES = {
    "IR": CountryRule("IR", "blocked", "Configured block"),
    "HU": CountryRule("HU", "gray", "Configured review"),
}


def test_international_number_detects_country_automatically() -> None:
    result = assess_phone_number("+36 30 123 4567", None, RULES)
    assert result.e164 == "+36301234567"
    assert result.country_code == "HU"
    assert result.risk == "gray"


def test_national_number_uses_selected_country() -> None:
    result = assess_phone_number("30 123 4567", "HU", RULES)
    assert result.e164 == "+36301234567"
    assert result.country_code == "HU"


def test_national_number_requires_country() -> None:
    with pytest.raises(PhoneValidationError, match="Choose a country"):
        assess_phone_number("30 123 4567", None, RULES)


def test_invalid_number_is_rejected() -> None:
    with pytest.raises(PhoneValidationError):
        assess_phone_number("123", "HU", RULES)
