import logging
import csv
import io
import asyncio
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.models.company import CompanyProfile
from app.models.compliance import ComplianceResult
from app.models.lead import LeadResult, LeadSubmission
from app.config import get_settings
from app.repositories import LeadRepository
from app.logging_config import configure_logging
from app.services.compliance import ComplianceService
from app.services.llm import LLMServiceError, OpenRouterLLMService
from app.services.research import CompanyResearchService
from app.services.crawler import CrawlError
from app.services.notifier import EmailNotifier
from app.services.pipeline import LeadPipeline
from app.services.phone_validation import (
    PhoneValidationError,
    assess_phone_number,
    supported_calling_codes,
)
from app.services.policy import load_country_rules

app = FastAPI(title="Maaz Sample Lead Validator")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
settings = get_settings()
configure_logging(settings)
llm = OpenRouterLLMService(settings)
research_service = CompanyResearchService(llm)
compliance_service = ComplianceService(llm)
repository = LeadRepository(settings.database_path)
pipeline = LeadPipeline(
    settings, repository, research_service, compliance_service, EmailNotifier(settings)
)
runs: dict[str, dict[str, object]] = {}


@app.get("/", include_in_schema=False)
async def frontend() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readme", include_in_schema=False)
async def readme_page() -> FileResponse:
    return FileResponse("app/static/readme.html")


class ResearchRequest(BaseModel):
    domain: str
    public_evidence: str = Field(min_length=1)


class ComplianceRequest(BaseModel):
    profile: CompanyProfile
    competitor_candidates: list[str] = Field(default_factory=list)
    restricted_jurisdictions: list[str] = Field(default_factory=list)


@app.exception_handler(LLMServiceError)
async def llm_error_handler(_: Request, exc: LLMServiceError) -> JSONResponse:
    logging.getLogger(__name__).error(
        "llm_service_unavailable", extra={"error_type": type(exc).__name__}
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "The AI service is temporarily unavailable."},
    )


@app.exception_handler(CrawlError)
async def crawl_error_handler(_: Request, exc: CrawlError) -> JSONResponse:
    logging.getLogger(__name__).warning(
        "lead_crawl_rejected", extra={"error_type": type(exc).__name__, "error": str(exc)}
    )
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(PhoneValidationError)
async def phone_error_handler(_: Request, exc: PhoneValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


class PhoneValidationRequest(BaseModel):
    phone_number: str
    country_code: str | None = None


@app.get("/api/policy/countries")
async def list_phone_countries() -> list[dict[str, str]]:
    rules = load_country_rules(settings.country_rules_path)
    return [
        {
            **option,
            "risk": rules.get(option["country_code"]).risk
            if option["country_code"] in rules else "standard",
        }
        for option in supported_calling_codes()
    ]


@app.post("/api/phone/validate")
async def validate_phone(request: PhoneValidationRequest) -> dict[str, str]:
    assessment = assess_phone_number(
        request.phone_number,
        request.country_code,
        load_country_rules(settings.country_rules_path),
    )
    return assessment.__dict__


@app.post("/api/leads", response_model=LeadResult)
async def create_lead(lead: LeadSubmission) -> LeadResult:
    return await pipeline.process(lead)


async def process_run(run_id: str, lead: LeadSubmission) -> None:
    async def progress(stage: str, message: str) -> None:
        runs[run_id].update({"stage": stage, "message": message})

    try:
        result = await pipeline.process(lead, progress)
        runs[run_id].update(
            {
                "status": "completed",
                "stage": "completed",
                "message": "Lead validation completed.",
                "result": result.model_dump(mode="json"),
            }
        )
    except Exception as exc:
        logging.getLogger(__name__).exception(
            "lead_run_failed", extra={"run_id": run_id, "error_type": type(exc).__name__}
        )
        if isinstance(exc, (PhoneValidationError, CrawlError)):
            message = str(exc)
        elif isinstance(exc, LLMServiceError):
            message = "The AI service is temporarily unavailable."
        else:
            message = "Lead validation could not be completed. Check the backend log."
        runs[run_id].update(
            {"status": "failed", "stage": "failed", "message": message}
        )


@app.post("/api/runs", status_code=202)
async def create_run(lead: LeadSubmission) -> dict[str, str]:
    run_id = uuid4().hex
    runs[run_id] = {
        "status": "running",
        "stage": "queued",
        "message": "Validation queued.",
    }
    asyncio.create_task(process_run(run_id, lead))
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, object]:
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Validation run not found.")
    return runs[run_id]


@app.get("/api/leads", response_model=list[LeadResult])
async def list_leads() -> list[LeadResult]:
    return repository.list()


@app.post("/api/leads/{lead_id}/notify", response_model=LeadResult)
async def resend_lead_notification(lead_id: int) -> LeadResult:
    result = repository.get(lead_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Lead not found.")
    notification_status = await pipeline.notifier.send(result)
    repository.update_notification(lead_id, notification_status)
    updated = result.model_copy(update={"notification_status": notification_status})
    if notification_status == "failed":
        raise HTTPException(
            status_code=502,
            detail="The report could not be sent. Check the SMTP event in logs/app.log.",
        )
    if notification_status == "skipped":
        raise HTTPException(
            status_code=503,
            detail="SMTP or a notification recipient is not configured.",
        )
    return updated


@app.get("/api/leads.csv")
async def export_leads_csv() -> StreamingResponse:
    def safe(value: object) -> object:
        if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
            return "'" + value
        return value

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([
        "Submitted", "Lead name", "Email", "Job title", "Company", "Website",
        "Email alignment", "Headquarters", "Employee estimate", "Cloud intensity",
        "Fit score", "Fit category", "Compliance", "Disposition", "Summary",
        "Notification",
    ])
    for result in reversed(repository.list(limit=10_000)):
        writer.writerow([safe(value) for value in [
            result.created_at.isoformat(), result.lead.name, str(result.lead.email),
            result.lead.job_title or "", result.profile.company, str(result.lead.website),
            result.email_alignment, result.profile.headquarters or "",
            result.profile.employee_estimate or "", result.profile.cloud_intensity,
            result.fit.score, result.fit.category, result.compliance.status,
            result.disposition, result.profile.summary, result.notification_status,
        ]])
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=lead-tracker.csv"},
    )
@app.post("/api/research", response_model=CompanyProfile)
async def research_company(request: ResearchRequest) -> CompanyProfile:
    return await research_service.research(request.domain, request.public_evidence)


@app.post("/api/compliance", response_model=ComplianceResult)
async def screen_company(request: ComplianceRequest) -> ComplianceResult:
    return await compliance_service.screen(
        request.profile,
        request.competitor_candidates,
        request.restricted_jurisdictions,
    )
