from pathlib import Path

from app.services.policy import load_competitors, load_country_rules


def test_policy_csv_files_load() -> None:
    competitors = load_competitors(str(Path("data/competitors.csv")))
    countries = load_country_rules(str(Path("data/country_rules.csv")))
    assert any(rule.name == "CloudTrim Inc" for rule in competitors)
    assert countries["IR"].risk == "blocked"
    assert countries["RU"].risk == "gray"
