"""AuditLog — append-only record of significant security/business events.

Immutable by policy (Constitution Principle VII): rows are only ever inserted, never
updated or deleted. The dossier-lifecycle events are declared now so later phases do not
require an enum migration.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDMixin

# Portable JSON: JSONB on Postgres, JSON elsewhere (e.g. SQLite in tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")


class AuditEvent(enum.StrEnum):
    # Authentication
    login_success = "login_success"
    login_failed = "login_failed"
    # Candidate dossier lifecycle (emitted from Phase 4 onward)
    cv_parsed = "cv_parsed"
    dossier_generated = "dossier_generated"
    score_computed = "score_computed"
    decision_recorded = "decision_recorded"
    pdf_exported = "pdf_exported"


class AuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event: Mapped[AuditEvent] = mapped_column(
        SAEnum(AuditEvent, name="audit_event"), nullable=False, index=True
    )
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
