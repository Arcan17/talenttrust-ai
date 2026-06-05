"""Candidate / document / consent response schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.candidate import CandidateStatus
from app.models.candidate_document import DocumentType


class ParsedProfile(BaseModel):
    language: str
    emails: list[str] = []
    phones: list[str] = []
    links: list[str] = []
    skills: list[str] = []
    char_count: int = 0


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    content_type: DocumentType
    size_bytes: int
    sha256: str
    parsed: ParsedProfile


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    version: str
    scope: str


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    vacancy_id: uuid.UUID
    display_name: str | None
    status: CandidateStatus
    document: DocumentOut | None = None
    consent: ConsentOut | None = None
