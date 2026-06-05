"""Model package — import all models so SQLAlchemy metadata and Alembic see them."""
from app.models.audit_log import AuditEvent, AuditLog
from app.models.organization import Organization
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
]
