import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import Settings
from app.models.lead import LeadResult

logger = logging.getLogger(__name__)


class EmailNotifier:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.smtp_host
            and self.settings.smtp_from_email
        )

    async def send(self, result: LeadResult) -> str:
        if not self.configured or not (
            result.lead.notification_email or self.settings.sales_notification_email
        ):
            logger.info(
                "smtp_notification_skipped",
                extra={"lead_id": result.id, "reason": "smtp_or_recipient_not_configured"},
            )
            return "skipped"
        try:
            await asyncio.to_thread(self._send_sync, result)
            logger.info(
                "smtp_notification_sent",
                extra={"lead_id": result.id, "smtp_host": self.settings.smtp_host, "smtp_port": self.settings.smtp_port},
            )
            return "sent"
        except (OSError, smtplib.SMTPException) as exc:
            logger.error(
                "smtp_notification_failed",
                extra={
                    "lead_id": result.id,
                    "smtp_host": self.settings.smtp_host,
                    "smtp_port": self.settings.smtp_port,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            return "failed"

    def _send_sync(self, result: LeadResult) -> None:
        message = EmailMessage()
        message["Subject"] = f"[{result.disposition.replace('_', ' ').title()}] {result.lead.company_name} — fit {result.fit.score}/100"
        message["From"] = self.settings.smtp_from_email
        message["To"] = str(
            result.lead.notification_email or self.settings.sales_notification_email
        )
        message.set_content(
            f"""New lead: {result.lead.name} <{result.lead.email}>
Company: {result.profile.company} ({result.profile.domain})
Fit: {result.fit.score}/100 — {result.fit.category}
Compliance: {result.compliance.status}
Disposition: {result.disposition.replace('_', ' ')}

Summary:
{result.profile.summary}

Compliance reasoning:
{result.compliance.reason}
"""
        )
        use_ssl = self.settings.smtp_use_ssl or self.settings.smtp_port == 465
        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as client:
            if self.settings.smtp_use_tls and not use_ssl:
                client.starttls()
            if self.settings.smtp_username:
                client.login(self.settings.smtp_username, self.settings.smtp_password)
            client.send_message(message)
