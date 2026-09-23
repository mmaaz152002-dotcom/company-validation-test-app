import logging
from collections.abc import Awaitable, Callable

from app.config import Settings
from app.models.company import CompanyProfile
from app.models.lead import LeadResult, LeadSubmission
from app.repositories import LeadRepository
from app.services.compliance import ComplianceService
from app.services.basic_screening import basic_compliance_screen
from app.services.crawler import crawl_website, evidence_text
from app.services.email_validation import assess_email_alignment
from app.services.disposition import decide_disposition
from app.services.fit_score import calculate_fit
from app.services.notifier import EmailNotifier
from app.services.research import CompanyResearchService, normalize_domain
from app.services.phone_validation import assess_phone_number
from app.services.policy import load_competitors, load_country_rules

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[str, str], Awaitable[None]]


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

    async def process(
        self, lead: LeadSubmission, progress: ProgressCallback | None = None
    ) -> LeadResult:
        async def report(stage: str, message: str) -> None:
            if progress:
                await progress(stage, message)

        await report("input_validation", "Lead fields validated.")
        domain = normalize_domain(str(lead.website))
        logger.info("lead_pipeline_started", extra={"company": lead.company_name, "domain": domain})
        email_alignment = assess_email_alignment(str(lead.email), domain)
        logger.info("lead_email_assessed", extra={"domain": domain, "email_alignment": email_alignment})
        country_rules = load_country_rules(self.settings.country_rules_path)
        competitors = load_competitors(self.settings.competitor_rules_path)
        phone = assess_phone_number(
            lead.phone_number or "", lead.phone_country_code, country_rules
        )
        lead = lead.model_copy(
            update={"phone_number": phone.e164, "phone_country_code": phone.country_code}
        )
        logger.info(
            "lead_phone_assessed",
            extra={"phone_country": phone.country_code, "phone_country_risk": phone.risk},
        )
        await report(
            "phone_validation",
            f"Phone validated: {phone.country_name} ({phone.risk} risk policy).",
        )
        await report("basic_screening", "Checking competitor and blocked-country rules.")
        basic_compliance = basic_compliance_screen(
            lead.company_name, domain, competitors, phone
        )
        if basic_compliance is not None:
            await report("blocked", basic_compliance.reason)
            logger.warning(
                "lead_blocked_by_basic_screening",
                extra={"domain": domain, "matched_rule": basic_compliance.matched_rule},
            )
            profile = CompanyProfile(
                company=lead.company_name,
                domain=domain,
                summary=(
                    "Company research was skipped because the submitted identity matched "
                    "a configured do-not-engage competitor rule during basic screening."
                ),
                business_model="Not researched",
                cloud_intensity="unknown",
                confidence=0.0,
            )
            fit = calculate_fit(profile, email_alignment)
            result = self.repository.create(
                lead, email_alignment, profile, fit, basic_compliance, "blocked",
                phone.country_name, phone.risk, phone.risk_reason,
                [
                    basic_compliance.reason,
                    "The lead was blocked before website research and did not consume an LLM call.",
                ],
            )
            notification_status = await self.notifier.send(result)
            self.repository.update_notification(result.id, notification_status)
            logger.info(
                "lead_pipeline_completed",
                extra={
                    "lead_id": result.id,
                    "disposition": "blocked",
                    "research_skipped": True,
                    "notification_status": notification_status,
                },
            )
            return result.model_copy(update={"notification_status": notification_status})

        profile = self.repository.get_cached_profile(domain)
        if profile is None:
            await report("website_crawl", "Crawling useful pages from the company website.")
            logger.info("company_cache_miss", extra={"domain": domain})
            pages = await crawl_website(str(lead.website), self.settings)
            evidence = evidence_text(pages)
            await report(
                "company_research",
                f"Generating a structured company profile from {len(pages)} page(s).",
            )
            profile = await self.research.research(domain, evidence)
            self.repository.cache_profile(domain, profile, evidence)
            logger.info("company_research_cached", extra={"domain": domain, "pages": len(pages)})
        else:
            logger.info("company_cache_hit", extra={"domain": domain})
            await report("company_research", "Using the cached company profile.")

        await report("fit_scoring", "Calculating the deterministic fit score.")
        fit = calculate_fit(profile, email_alignment)
        await report("compliance", "Running detailed compliance screening.")
        compliance = await self.compliance.screen(
            profile,
            [competitor.name for competitor in competitors],
            [
                "Countries and territories subject to comprehensive US sanctions or broad export controls",
                "Entities based in jurisdictions that require enhanced sanctions review",
                f"Validated phone country: {phone.country_name}; configured risk: {phone.risk}; reason: {phone.risk_reason}",
            ],
        )
        disposition, decision_reasons = decide_disposition(
            compliance, fit.score, phone.risk, phone.risk_reason, email_alignment
        )

        await report("persistence", "Saving the result to the sales tracker.")
        result = self.repository.create(
            lead, email_alignment, profile, fit, compliance, disposition,
            phone.country_name, phone.risk, phone.risk_reason,
            decision_reasons,
        )
        logger.info(
            "lead_persisted",
            extra={"lead_id": result.id, "domain": domain, "fit_score": fit.score, "compliance_status": compliance.status, "disposition": disposition},
        )
        await report("notification", "Sending the email report.")
        notification_status = await self.notifier.send(result)
        self.repository.update_notification(result.id, notification_status)
        logger.info("lead_pipeline_completed", extra={"lead_id": result.id, "notification_status": notification_status})
        return result.model_copy(update={"notification_status": notification_status})
