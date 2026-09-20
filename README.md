# Maaz Sample Lead Validator

This is a local-first FastAPI prototype for researching inbound sales leads, scoring
their fit for Docktape's cloud-cost optimization service, screening them against a
do-not-engage policy, tracking the results, and notifying sales.

## Run it

1. Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`.
2. Optionally configure the SMTP fields and `SALES_NOTIFICATION_EMAIL`.
3. Install with `pip install -e ".[test]"`.
4. Run `uvicorn app.main:app --reload`.
5. Open `http://127.0.0.1:8000`.

The UI accepts name, work email, company name, company website, an optional job title,
and the email address that should receive the completed report. Job title was added
because it gives sales useful buying-role context without asking the prospect for facts
the application can research itself. The tracker keeps its compact main columns; each
row expands to show the full profile, evidence sources, cloud signals, scoring breakdown,
compliance reasoning, and delivery status. These display details are intentionally not
added to the CSV export.

## Pipeline

`POST /api/leads` validates the submission, compares email and website domains, crawls
up to ten useful same-domain pages, builds or reuses a company profile, calculates fit,
runs compliance screening, stores the result in SQLite, and attempts an SMTP
notification. `GET /api/leads` supplies the UI tracker and `GET /api/leads.csv` exports
the tracker in a format that opens in Excel or Google Sheets.

The crawler prioritizes home, about, contact, product, service, careers, legal, pricing,
and customer pages. It removes scripts, styles, navigation, footers, and other page
chrome, preserves useful headings and text, caps response sizes, and rejects local or
private network targets. The company website is the primary data source because it is
available for every submission, directly attributable, inexpensive, and easy to cache.

## Fit scoring

The final score is deterministic Python, not another model judgment. The research model
extracts evidence; these documented rules turn it into an explainable 100-point score:

| Component | Maximum | Method |
|---|---:|---|
| Company size | 35 | 3 points for 1–10 employees, 10 for 11–50, 22 for 51–200, 30 for 201–999, and 35 for 1,000+ |
| Cloud intensity | 40 | Base points from unknown/low/medium/high intensity, plus up to 5 points for distinct cloud signals, capped at 40 |
| Business model | 15 | Highest for SaaS, software, platform, cloud, data, or marketplace businesses; partial credit for other digital/technology models |
| Lead quality | 10 | 10 for a matching company email domain, 4 for a mismatch, 2 for a free provider, and 0 for invalid input |

Scores map to `strong` (75–100), `promising` (50–74), `borderline` (25–49), and
`low` (0–24). Compliance is a separate gate. A blocked company remains blocked regardless
of score; ambiguous compliance, scores below 50, and non-company email addresses go to
manual review.

## Compliance approach

The configured fictional competitor list is CloudTrim Inc, SpendWise Cloud, and
RightSize Cloud Co. The company profile and policy are evaluated in one structured LLM
call, which is instructed to reason about punctuation, corporate suffixes, word spacing,
partial names, and plausible near-matches. The result must be `pass`, `review`, or
`block`, with a matched rule, possible match, confidence, and reason. Headquarters are
also screened against a general comprehensive-sanctions/export-control policy. This is a
sales triage aid, not legal advice.

## Storage and exports

SQLite stores leads and cached company profiles in `data/leads.db`. Pgvector was omitted
because each company has a small, bounded evidence set that fits in one research request;
semantic retrieval would add operational complexity without improving this prototype.
The UI presents a skimmable tracker and exports persisted records as CSV. CSV values are
escaped defensively to avoid spreadsheet-formula injection.

SMTP is optional. If it is not configured, completed results are stored with notification
status `skipped`; notification failure does not discard a successfully processed lead.
Port 465 automatically uses implicit TLS through `SMTP_SSL`; other ports use STARTTLS
when `SMTP_USE_TLS=true`. `SMTP_USE_SSL` can explicitly enable implicit TLS. Every
expanded tracker row includes a Send email report button for retrying delivery.

## Backend logs

Structured JSON logs are written to `logs/app.log` and rotated at approximately 2 MB.
The crawler records every attempted URL, redirect, HTTP status, content type, extraction
result, and sanitized exception. The pipeline records cache usage, scoring, compliance,
persistence, and notification status. API keys, SMTP passwords, authorization headers,
and submitted email addresses are not written to the log. Configure the location and
verbosity with `LOG_FILE` and `LOG_LEVEL`.

## AI coding tools

The project was built with OpenAI Codex as the coding assistant. Codex was used to turn
the product requirements into a scoped architecture, implement the FastAPI services and
frontend, write tests, validate OpenRouter conventions against official documentation,
and iterate on the runnable prototype. `AGENTS.md` captures the guardrails used to keep
future AI changes focused and minimize unnecessary LLM calls.

Run the server with `uvicorn app.main:app --reload`, then open
`http://127.0.0.1:8000` for the lead validation form. The server exposes
`POST /api/research` and `POST /api/compliance`; exhausted model fallbacks produce a
controlled HTTP 503 response without exposing credentials or internal exception details.

## LLM Architecture

The application uses OpenRouter as its single server-side LLM gateway. No browser code
receives the API key and no provider-specific SDK is used. Research and compliance code
define what to ask; `app/services/llm.py` alone handles networking, model selection,
timeouts, bounded retries, JSON extraction, Pydantic validation, usage logging, and safe
errors.

The default preference is:

1. `z-ai/glm-5.2:free`
2. `openrouter/free`
3. `qwen/qwen3.7-flash`
4. Any optional Gemini model only when its verified OpenRouter ID is explicitly added
   to `OPENROUTER_FALLBACK_MODELS`

All IDs and their priority are environment-configurable because availability—especially
for free models—can change. Each model receives one retry before the next model is tried,
which improves demo reliability without creating unbounded retry loops. Authentication
failures stop immediately.

For a newly researched company the normal flow uses approximately two successful
reasoning operations: one complete company-profile generation and one compliance
screening. Research is cached in-process by normalized company domain, so subsequent
leads at the same company reuse the profile and do not repeat the research call. Replace
the cache dictionary with the application's persistent cache when integrating this layer.

OpenRouter requests use `/api/v1/chat/completions`, Bearer authentication, optional
`HTTP-Referer` and `X-OpenRouter-Title` identification headers, and JSON Schema response
format. Responses are still parsed defensively, including Markdown JSON fences, and are
never accepted without Pydantic validation.

## Configuration

See `.env.example`. `OPENROUTER_FALLBACK_MODELS` is a comma-separated ordered list.
Never commit `.env` or a real API key.

## Verification sources

- [OpenRouter quickstart](https://openrouter.ai/docs/quickstart)
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Model catalog](https://openrouter.ai/models)
