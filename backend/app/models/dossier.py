"""Dossier — the assembled, evidence-based candidate evaluation.

Holds the professional summary, skills-with-evidence, gaps, neutral inconsistencies, suggested
interview questions and a non-binding recommendation. Every stored conclusion carries an
evidence reference (Constitution Principle I); the dossier service enforces this guardrail.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.score import Recommendation

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Dossier(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "dossiers"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    vacancy_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    skills: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    gaps: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    inconsistencies: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    interview_questions: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    recommendation: Mapped[Recommendation] = mapped_column(
        SAEnum(Recommendation, name="score_recommendation"), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
