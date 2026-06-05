"""Candidate — a person evaluated against a vacancy.

In Phase 1 the candidate has no login; they exist from the CV the recruiter uploads.
`status` is operational only (received/analyzed) and is NEVER a hiring outcome — a final
outcome exists solely as a human-recorded Decision (Constitution Principle IX).
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class CandidateStatus(enum.StrEnum):
    received = "received"
    analyzed = "analyzed"


class Candidate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidates"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[CandidateStatus] = mapped_column(
        SAEnum(CandidateStatus, name="candidate_status"),
        nullable=False,
        default=CandidateStatus.received,
    )
