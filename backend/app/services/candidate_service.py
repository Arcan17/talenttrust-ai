"""Candidate / document / consent business logic — organization-scoped.

Uploading a CV requires consent (captured at upload) and parses the document before any
row is committed; the `cv_parsed` audit event is emitted on success. No analysis beyond
text extraction + basic structuring happens here (scoring/dossier land in Phase 4b).
"""
from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEvent
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument, DocumentType
from app.models.consent import Consent
from app.models.vacancy import Vacancy
from app.services import audit_service, cv_parser


class NotFoundError(Exception):
    """Raised when a candidate/vacancy is not found within the caller's organization."""


async def _get_org_vacancy(
    db: AsyncSession, *, organization_id: uuid.UUID, vacancy_id: uuid.UUID
) -> Vacancy:
    vacancy = await db.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.organization_id != organization_id:
        raise NotFoundError("Vacancy not found")
    return vacancy


async def create_candidate_with_cv(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    vacancy_id: uuid.UUID,
    filename: str | None,
    declared_content_type: str | None,
    data: bytes,
    consent_version: str,
    consent_scope: str,
    display_name: str | None = None,
) -> tuple[Candidate, CandidateDocument, Consent]:
    """Validate+parse the CV, then persist candidate, document and consent atomically.

    Raises cv_parser.CVParseError subclasses on rejection (mapped to HTTP by the router),
    and NotFoundError if the vacancy is not in the caller's organization.
    """
    await _get_org_vacancy(db, organization_id=organization_id, vacancy_id=vacancy_id)

    # Parse first; if the CV is invalid we never create any row.
    content_type, parsed, raw_text = cv_parser.parse_cv(
        filename=filename, declared_content_type=declared_content_type, data=data
    )

    candidate = Candidate(
        organization_id=organization_id,
        vacancy_id=vacancy_id,
        display_name=display_name,
    )
    db.add(candidate)
    await db.flush()

    document = CandidateDocument(
        organization_id=organization_id,
        candidate_id=candidate.id,
        filename=filename or "cv",
        content_type=DocumentType(content_type),
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        raw_text=raw_text,
        parsed=parsed.to_dict(),
    )
    consent = Consent(
        organization_id=organization_id,
        candidate_id=candidate.id,
        version=consent_version,
        scope=consent_scope,
        granted_by_user_id=actor_user_id,
    )
    db.add(document)
    db.add(consent)

    await audit_service.record(
        db,
        event=AuditEvent.cv_parsed,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type="candidate",
        target_id=candidate.id,
        meta={
            "content_type": content_type,
            "char_count": parsed.char_count,
            "language": parsed.language,
        },
    )

    await db.commit()
    await db.refresh(candidate)
    await db.refresh(document)
    await db.refresh(consent)
    return candidate, document, consent


async def get_candidate_bundle(
    db: AsyncSession, *, organization_id: uuid.UUID, candidate_id: uuid.UUID
) -> tuple[Candidate, CandidateDocument | None, Consent | None]:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")
    document = await db.scalar(
        select(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)
    )
    consent = await db.scalar(
        select(Consent)
        .where(Consent.candidate_id == candidate_id)
        .order_by(Consent.created_at.desc())
    )
    return candidate, document, consent


async def has_consent(db: AsyncSession, *, candidate_id: uuid.UUID) -> bool:
    """Whether a valid consent exists for this candidate (gate for Phase 4b analysis)."""
    row = await db.scalar(
        select(Consent.id).where(Consent.candidate_id == candidate_id).limit(1)
    )
    return row is not None
