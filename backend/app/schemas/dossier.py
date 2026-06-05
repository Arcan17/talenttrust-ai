"""Dossier schemas.

Every materially important conclusion (skill, gap, inconsistency, question) carries at least
one EvidenceItem citing its source (Constitution Principle I). Recommendations are non-binding
(Principle IX). Inconsistencies use neutral language only.
"""
from __future__ import annotations

import enum
import uuid

from pydantic import BaseModel, ConfigDict

from app.models.candidate import CandidateStatus
from app.models.score import Recommendation


class EvidenceSource(enum.StrEnum):
    cv = "cv"
    vacancy = "vacancy"
    score_breakdown = "score_breakdown"
    system_rule = "system_rule"


class EvidenceItem(BaseModel):
    source: EvidenceSource
    detail: str


class SkillEvidence(BaseModel):
    name: str
    required: bool
    evidence: list[EvidenceItem]


class GapItem(BaseModel):
    requirement: str
    note: str
    evidence: list[EvidenceItem]


class InconsistencyItem(BaseModel):
    signal: str
    message: str  # neutral language only
    severity: str
    evidence: list[EvidenceItem]


class InterviewQuestion(BaseModel):
    question: str
    rationale: str
    based_on: str  # "gap" | "inconsistency" | "skill"
    evidence: list[EvidenceItem]


class DossierSummary(BaseModel):
    text: str
    score: int
    recommendation: Recommendation
    evidence: list[EvidenceItem]


class DossierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    vacancy_id: uuid.UUID
    status: CandidateStatus
    summary: DossierSummary
    skills: list[SkillEvidence]
    gaps: list[GapItem]
    inconsistencies: list[InconsistencyItem]
    interview_questions: list[InterviewQuestion]
    recommendation: Recommendation
