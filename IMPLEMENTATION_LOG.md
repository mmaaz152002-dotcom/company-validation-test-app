# Implementation log

## Current architecture

- FastAPI with a dependency-free HTML/CSS/JavaScript frontend.
- OpenRouter-only structured company research and compliance screening.
- SQLite persistence and domain-based company research caching.
- Deterministic fit scoring with a stored component breakdown.
- Same-domain website crawler capped at ten pages.
- UI lead tracker with CSV export.
- Optional SMTP notification configured entirely through environment variables.

## Scope decisions

- Pgvector was intentionally omitted. A bounded crawl fits in one research request and does not require semantic retrieval.
- React was intentionally omitted because the interface has one submission workflow and one tracker table.
- CSV is generated from persisted SQLite records and opens directly in Excel or Google Sheets.

