"""Model package — import all models so SQLAlchemy metadata and Alembic see them."""
from app.models.audit_log import AuditEvent, AuditLog
from app.models.candidate import Candidate, CandidateStatus
from app.models.candidate_document import CandidateDocument, DocumentType
from app.models.consent import Consent
from app.models.organization import Organization
from app.models.score import Recommendation, Score
from app.models.user import Role, User
from app.models.vacancy import Modality, Seniority, Vacancy, VacancyStatus

__all__ = [
    "Organization",
    "User",
    "Role",
    "AuditLog",
    "AuditEvent",
    "Vacancy",
    "Modality",
    "Seniority",
    "VacancyStatus",
    "Candidate",
    "CandidateStatus",
    "CandidateDocument",
    "DocumentType",
    "Consent",
    "Score",
    "Recommendation",
]
