import logging

from app.config import Settings
from app.models.lead import LeadResult, LeadSubmission
from app.repositories import LeadRepository
from app.services.compliance import ComplianceService
from app.services.crawler import crawl_website, evidence_text
from app.services.email_validation import assess_email_alignment
from app.services.fit_score import calculate_fit
from app.services.notifier import EmailNotifier
from app.services.research import CompanyResearchService, normalize_domain

logger = logging.getLogger(__name__)


class LeadPipeline:
    def __init__(
        self,
        settings: Settings,
        repository: LeadRepository,
        research: CompanyResearchService,
        compliance: ComplianceService,
        notifier: EmailNotifier,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.research = research
        self.compliance = compliance
        self.notifier = notifier

    async def process(self, lead: LeadSubmission) -> LeadResult:
        domain = normalize_domain(str(lead.website))
        logger.info("lead_pipeline_started", extra={"company": lead.company_name, "domain": domain})
        email_alignment = assess_email_alignment(str(lead.email), domain)
        logger.info("lead_email_assessed", extra={"domain": domain, "email_alignment": email_alignment})
        profile = self.repository.get_cached_profile(domain)
        if profile is None:
            logger.info("company_cache_miss", extra={"domain": domain})
            pages = await crawl_website(str(lead.website), self.settings)
            evidence = evidence_text(pages)
            profile = await self.research.research(domain, evidence)
            self.repository.cache_profile(domain, profile, evidence)
            logger.info("company_research_cached", extra={"domain": domain, "pages": len(pages)})
        else:
            logger.info("company_cache_hit", extra={"domain": domain})

        fit = calculate_fit(profile, email_alignment)
        compliance = await self.compliance.screen(
            profile,
            ["CloudTrim Inc", "SpendWise Cloud", "RightSize Cloud Co"],
            [
                "Countries and territories subject to comprehensive US sanctions or broad export controls",
                "Entities based in jurisdictions that require enhanced sanctions review",
            ],
        )
        if compliance.status == "block":
            disposition = "blocked"
        elif compliance.status == "review" or fit.score < 50 or email_alignment in {"domain_mismatch", "free_email_provider"}:
            disposition = "manual_review"
        else:
            disposition = "sales_ready"

        result = self.repository.create(lead, email_alignment, profile, fit, compliance, disposition)
        logger.info(
            "lead_persisted",
            extra={"lead_id": result.id, "domain": domain, "fit_score": fit.score, "compliance_status": compliance.status, "disposition": disposition},
        )
        notification_status = await self.notifier.send(result)
        self.repository.update_notification(result.id, notification_status)
        logger.info("lead_pipeline_completed", extra={"lead_id": result.id, "notification_status": notification_status})
        return result.model_copy(update={"notification_status": notification_status})
