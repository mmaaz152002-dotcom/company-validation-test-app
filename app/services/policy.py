import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CompetitorRule:
    name: str
    aliases: tuple[str, ...]
    domains: tuple[str, ...]


@dataclass(frozen=True)
class CountryRule:
    iso2: str
    risk: str
    reason: str


def load_competitors(path: str) -> tuple[CompetitorRule, ...]:
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        return tuple(
            CompetitorRule(
                name=row["name"].strip(),
                aliases=tuple(value.strip() for value in row.get("aliases", "").split("|") if value.strip()),
                domains=tuple(value.strip().lower() for value in row.get("domains", "").split("|") if value.strip()),
            )
            for row in rows
            if row.get("name", "").strip()
            and row.get("enabled", "true").strip().lower() in {"1", "true", "yes"}
        )


def load_country_rules(path: str) -> dict[str, CountryRule]:
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        rules = {}
        for row in rows:
            iso2 = row.get("iso2", "").strip().upper()
            risk = row.get("risk", "").strip().lower()
            if len(iso2) != 2 or risk not in {"blocked", "gray"}:
                continue
            rules[iso2] = CountryRule(iso2, risk, row.get("reason", "").strip())
        return rules

