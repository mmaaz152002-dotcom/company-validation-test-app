import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from app.models.company import CompanyProfile
from app.models.compliance import ComplianceResult
from app.models.lead import FitResult, LeadResult, LeadSubmission


class LeadRepository:
    def __init__(self, database_path: str) -> None:
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS company_cache (
                    domain TEXT PRIMARY KEY, profile_json TEXT NOT NULL,
                    evidence TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                    lead_json TEXT NOT NULL, email_alignment TEXT NOT NULL,
                    profile_json TEXT NOT NULL, fit_json TEXT NOT NULL,
                    compliance_json TEXT NOT NULL, disposition TEXT NOT NULL,
                    notification_status TEXT NOT NULL
                );
            """)

    def get_cached_profile(self, domain: str) -> CompanyProfile | None:
        with self.lock, self._connect() as connection:
            row = connection.execute("SELECT profile_json FROM company_cache WHERE domain = ?", (domain,)).fetchone()
        return CompanyProfile.model_validate_json(row["profile_json"]) if row else None

    def cache_profile(self, domain: str, profile: CompanyProfile, evidence: str) -> None:
        with self.lock, self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO company_cache(domain, profile_json, evidence, updated_at) VALUES(?,?,?,?)",
                (domain, profile.model_dump_json(), evidence, datetime.now(UTC).isoformat()),
            )

    def create(self, lead: LeadSubmission, email_alignment: str, profile: CompanyProfile, fit: FitResult, compliance: ComplianceResult, disposition: str) -> LeadResult:
        created_at = datetime.now(UTC)
        with self.lock, self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO leads(created_at,lead_json,email_alignment,profile_json,fit_json,compliance_json,disposition,notification_status) VALUES(?,?,?,?,?,?,?,?)",
                (created_at.isoformat(), lead.model_dump_json(), email_alignment, profile.model_dump_json(), fit.model_dump_json(), compliance.model_dump_json(), disposition, "skipped"),
            )
            lead_id = int(cursor.lastrowid)
        return LeadResult(id=lead_id, created_at=created_at, lead=lead, email_alignment=email_alignment, profile=profile, fit=fit, compliance=compliance, disposition=disposition, notification_status="skipped")

    def update_notification(self, lead_id: int, status: str) -> None:
        with self.lock, self._connect() as connection:
            connection.execute("UPDATE leads SET notification_status=? WHERE id=?", (status, lead_id))

    def list(self, limit: int = 200) -> list[LeadResult]:
        with self.lock, self._connect() as connection:
            rows = connection.execute("SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._to_result(row) for row in rows]

    def get(self, lead_id: int) -> LeadResult | None:
        with self.lock, self._connect() as connection:
            row = connection.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return self._to_result(row) if row else None

    @staticmethod
    def _to_result(row: sqlite3.Row) -> LeadResult:
        return LeadResult(
            id=row["id"], created_at=row["created_at"],
            lead=LeadSubmission.model_validate_json(row["lead_json"]),
            email_alignment=row["email_alignment"],
            profile=CompanyProfile.model_validate_json(row["profile_json"]),
            fit=FitResult.model_validate_json(row["fit_json"]),
            compliance=ComplianceResult.model_validate_json(row["compliance_json"]),
            disposition=row["disposition"], notification_status=row["notification_status"],
        )
