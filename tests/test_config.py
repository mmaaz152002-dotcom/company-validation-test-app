from app.config import Settings


def test_fallback_models_are_parsed_and_deduplicated() -> None:
    settings = Settings(
        openrouter_primary_model="primary",
        openrouter_fallback_models="fallback, primary, last",
    )
    assert settings.openrouter_models == ["primary", "fallback", "last"]

