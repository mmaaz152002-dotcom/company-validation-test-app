# Project guardrails

- OpenRouter is the only LLM gateway. All calls go through `app/services/llm.py`.
- Target two successful LLM operations per newly researched company: one research call and one compliance call.
- Reuse cached research by normalized domain. Never call the model once per page or profile field.
- Keep crawling, email/domain checks, fit scoring, persistence, CSV export, and notification deterministic.
- Never expose OpenRouter or SMTP credentials to browser JavaScript, logs, API responses, or committed files.
- Keep the prototype local-first: FastAPI, plain HTML/CSS/JS, and SQLite. Do not add a vector database.
- Crawl no more than ten useful same-domain pages and block private/local network targets.
- Compliance output is a sales-screening aid, not legal advice. Ambiguous matches require manual review.
- Add or update tests for business rules and run the suite after meaningful changes.
- Record architectural decisions in `IMPLEMENTATION_LOG.md`; do not use this file as a running change log.

