"""CandidateDocument — the uploaded CV (PDF/DOCX) with extracted text and parsed profile.

Only text-extractable PDF/DOCX up to 5 MB are accepted (validated by the CV parser before
a row is created). `raw_text` holds the extracted text; `parsed` holds the basic structured
profile (language, emails, skills, ...). No external enrichment (LinkedIn/GitHub) occurs.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDMixin

JSONType = JSON().with_variant(JSONB(), "postgresql")


class DocumentType(enum.StrEnum):
    pdf = "pdf"
    docx = "docx"


class CandidateDocument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "candidate_documents"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"), nullable=False
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    parsed: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
