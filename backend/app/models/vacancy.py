"""Vacancy — the structured job opening a candidate is evaluated against.

The reference for candidate↔vacancy scoring (US2). `requirements_embedding` is declared
here but left nullable in Phase 3; it is populated when scoring lands (Phase 4), so the
vacancy CRUD stays free of embedding dependencies and tests remain offline.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.config import settings
from app.db.base import Base, TimestampMixin, UUIDMixin
from app.db.types import Embedding


class Modality(enum.StrEnum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class Seniority(enum.StrEnum):
    junior = "junior"
    mid = "mid"
    senior = "senior"


class VacancyStatus(enum.StrEnum):
    open = "open"
    closed = "closed"


class Vacancy(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "vacancies"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    required_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    desired_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    modality: Mapped[Modality] = mapped_column(
        SAEnum(Modality, name="vacancy_modality"), nullable=False
    )
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seniority: Mapped[Seniority] = mapped_column(
        SAEnum(Seniority, name="vacancy_seniority"), nullable=False
    )
    status: Mapped[VacancyStatus] = mapped_column(
        SAEnum(VacancyStatus, name="vacancy_status"),
        nullable=False,
        default=VacancyStatus.open,
    )
    # Populated in Phase 4 (scoring); nullable so Phase 3 CRUD needs no embeddings.
    requirements_embedding: Mapped[list[float] | None] = mapped_column(
        Embedding(settings.embedding_dim), nullable=True
    )
