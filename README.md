# Lead Qualification AI Prototype

## Docker deployment

Build the image from the repository root:

```bash
docker build -t maaz-lead-validator .
```

Run it with the local `.env` file and persistent data/log directories:

```bash
docker run --name maaz-lead-validator \
  --env-file .env \
  -p 8000:8000 \
  -v "$(pwd)/data:/app/data" \
  -v "$(pwd)/logs:/app/logs" \
  maaz-lead-validator
```

PowerShell equivalent:

```powershell
docker run --name maaz-lead-validator `
  --env-file .env `
  -p 8000:8000 `
  -v "${PWD}/data:/app/data" `
  -v "${PWD}/logs:/app/logs" `
  maaz-lead-validator
```

The container runs as a non-root user, listens on port 8000, and exposes `/health` for
platform health checks. Mount `/app/data` to preserve SQLite records and `/app/logs` to
preserve structured logs. Provide secrets through `.env` or the deployment platform;
never copy `.env` into the image.

This project is an AI-assisted lead qualification workflow that researches a company, evaluates commercial fit, performs compliance screening, and routes the lead to one of three outcomes:

* Sales Ready
* Manual Review
* Blocked

The goal is to reduce manual research and triage work while keeping the decision process explainable and auditable.

## AI Coding Tools

I used **OpenAI Codex** as my primary AI coding assistant during development.

I treated it as a pair-programming tool rather than as an autonomous code generator. I used it mainly for:

* implementing individual components after defining the expected logic
* debugging and identifying edge cases
* refactoring
* validating implementation ideas
* iterating faster on backend behavior
* discussing architectural and algorithmic trade-offs

The overall workflow, scoring logic, routing rules, and system architecture were defined intentionally rather than delegated entirely to the coding agent.

I also regularly use **MCP-based workflows** when working with AI coding agents, mainly to give the agent access to relevant tools and context during development.

## Data Source Choice

The submitted company website is used as the primary source for company research.

The crawler starts from the submitted domain and prioritizes business-relevant pages such as:

* About
* Company
* Products
* Services
* Pricing
* Careers
* Contact
* Legal and policy pages

I chose the company's own website because it provides a relatively direct and explainable source of information while avoiding unnecessary dependency on paid enrichment APIs for this prototype.

The extracted content is cleaned before being passed to the LLM. Navigation, scripts, forms, and other low-value page content are removed so that the model receives mostly business-relevant evidence.

The LLM is instructed to use only the supplied evidence and return unknown values when the website does not provide enough information.

Company research is cached by normalized domain so repeated leads from the same company do not trigger another crawl and research call.

## Definition of Fit

Fit is calculated deterministically from facts extracted during company research.

The LLM does not directly decide whether a lead is a good fit. Its role is to structure company information. A deterministic scoring layer then turns those facts into a score.

The current score is based on four dimensions:

### Company size — up to 35 points

Larger companies currently receive more points because the assumed target customer is more likely to have sufficient infrastructure complexity and commercial value.

### Cloud intensity — up to 40 points

Cloud maturity is the most heavily weighted component.

Signals can include technologies or operational indicators such as:

* AWS
* Azure
* Google Cloud
* Kubernetes
* Terraform
* DevOps or SRE hiring
* data platforms
* multi-region infrastructure

### Business model — up to 15 points

Software, SaaS, platform, cloud, data, and marketplace businesses receive the highest relevance score.

### Lead quality — up to 10 points

The system evaluates whether the submitted work email matches the company domain.

A company-domain email receives the highest score, while free-email providers and domain mismatches reduce lead quality.

The final fit score is grouped into:

* 75–100: Strong
* 50–74: Promising
* 25–49: Borderline
* 0–24: Low

The scoring logic is intentionally simple and transparent for this prototype. In a production environment, the weights would ideally be calibrated using historical conversion and customer-value data.

## Compliance and Fuzzy Matching

Compliance screening currently checks two areas:

* potential competitor matches
* restricted or higher-risk jurisdictions

Company names are normalized before comparison by removing:

* capitalization differences
* punctuation
* spacing
* common legal suffixes such as Inc., LLC, Ltd., Corp., and similar forms

For example:

`CloudTrim Inc.`
and
`Cloud Trim LLC`

both normalize to approximately the same underlying name.

After normalization, fuzzy string similarity is calculated between the researched company and configured competitor names.

The similarity score is used as supporting evidence rather than as the final decision.

The compliance model receives:

* the researched company profile
* possible competitor matches
* similarity scores
* headquarters information
* jurisdiction policy

It must distinguish between:

* a confirmed match
* a plausible partial or fuzzy match
* an unrelated company

This avoids blocking companies based only on a similar-looking name.

Ambiguous cases are routed to **Manual Review** instead of being automatically blocked.

## Final Routing Logic

The final disposition combines fit, compliance, and email quality.

A lead is **Blocked** when compliance returns a confirmed block.

A lead is sent to **Manual Review** when:

* compliance is uncertain
* fit score is below 50
* the email domain does not match the company
* a free email provider is used

All remaining leads are marked **Sales Ready**.

This intentionally separates commercial fit from risk and identity signals. A company can have a high fit score and still require manual review.

## Other Assumptions

This is a prototype, so several assumptions were made intentionally.

The company website is treated as the main source of truth, even though company websites may be incomplete or outdated.

Employee count and cloud maturity are estimates based only on available public evidence.

The system does not verify whether an email mailbox actually exists. It checks email syntax, provider type, and domain alignment only.

Fit weights are manually defined and have not yet been trained or calibrated using historical sales data.

Competitor and jurisdiction rules are currently configured manually. In a production system, these should ideally be maintained outside the application code so business or compliance teams can update them without developer involvement.

The crawler limits the number of pages it processes to control latency, token usage, and irrelevant context.

Structured LLM outputs are validated before use, and fallback models are available if the primary model fails or returns unusable output.

The main design principle is to use AI for tasks where interpretation is useful, while keeping important business decisions such as scoring and final routing as deterministic and explainable as possible.
