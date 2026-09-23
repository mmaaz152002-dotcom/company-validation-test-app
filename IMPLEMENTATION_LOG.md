# Implementation log

## Current architecture

- FastAPI with a dependency-free HTML/CSS/JavaScript frontend.
- OpenRouter-only structured company research and compliance screening.
- SQLite persistence and domain-based company research caching.
- Deterministic fit scoring with a stored component breakdown.
- Same-domain website crawler capped at ten pages.
- UI lead tracker with CSV export.
- Optional SMTP notification configured entirely through environment variables.
- Phone numbers are normalized with libphonenumber. Country risk and competitor rules
  are loaded from editable CSV files for each submission.
- Validation runs expose real pipeline stage updates through an in-memory polling API;
  the UI does not simulate LLM progress.

## Scope decisions

- Pgvector was intentionally omitted. A bounded crawl fits in one research request and does not require semantic retrieval.
- React was intentionally omitted because the interface has one submission workflow and one tracker table.
- CSV is generated from persisted SQLite records and opens directly in Excel or Google Sheets.
- Phone country is treated as a policy signal: blocked countries stop before research,
  gray countries continue through research but require manual review.
- Every persisted result includes deterministic decision reasons that identify the exact
  rules responsible for blocked, manual-review, or sales-ready routing.
## Explainable disposition decisions

- Persist every deterministic routing trigger with each lead rather than showing only the final disposition.
- Display these reasons in the immediate result, expanded tracker row, and email report.
- Keep routing logic in a standalone deterministic service so block, manual-review, and sales-ready outcomes can be unit tested independently of crawling and LLM output.
