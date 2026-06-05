"""Candidate endpoints — CV upload with consent + retrieval (US2, Phase 4a).

Upload requires consent (captured inline) and write role (org_admin/recruiter). The CV is
validated and parsed before any row is created; rejection maps to 400/413. Scoring and the
dossier are NOT produced here (Phase 4b).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument
from app.models.consent import Consent
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.candidate import CandidateOut, ConsentOut, DocumentOut
from app.services import candidate_service, cv_parser, retention_service

router = APIRouter(tags=["candidates"])

_writer = require_role(Role.org_admin, Role.recruiter)
_admin = require_role(Role.org_admin)


def _to_out(
    candidate: Candidate,
    document: CandidateDocument | None,
    consent: Consent | None,
) -> CandidateOut:
    return CandidateOut(
        id=candidate.id,
        organization_id=candidate.organization_id,
        vacancy_id=candidate.vacancy_id,
        display_name=candidate.display_name,
        status=candidate.status,
        document=DocumentOut.model_validate(document) if document is not None else None,
        consent=ConsentOut.model_validate(consent) if consent is not None else None,
    )


@router.post(
    "/vacancies/{vacancy_id}/candidates",
    response_model=CandidateOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_candidate(
    vacancy_id: uuid.UUID,
    file: UploadFile = File(...),
    consent_version: str = Form(..., min_length=1),
    consent_scope: str = Form(..., min_length=1),
    display_name: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_writer),
) -> CandidateOut:
    data = await file.read()
    try:
        candidate, document, consent = await candidate_service.create_candidate_with_cv(
            db,
            organization_id=current.organization_id,
            actor_user_id=current.id,
            vacancy_id=vacancy_id,
            filename=file.filename,
            declared_content_type=file.content_type,
            data=data,
            consent_version=consent_version,
            consent_scope=consent_scope,
            display_name=display_name,
        )
    except candidate_service.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except cv_parser.FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except (cv_parser.UnsupportedFormatError, cv_parser.NoTextExtractedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return _to_out(candidate, document, consent)


@router.get("/candidates/{candidate_id}", response_model=CandidateOut)
async def get_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> CandidateOut:
    try:
        candidate, document, consent = await candidate_service.get_candidate_bundle(
            db, organization_id=current.organization_id, candidate_id=candidate_id
        )
    except candidate_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        ) from exc
    return _to_out(candidate, document, consent)


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_candidate(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_admin),
) -> None:
    """Hard-delete a candidate and all linked personal data (org_admin only)."""
    try:
        await retention_service.delete_candidate(
            db,
            organization_id=current.organization_id,
            actor_user_id=current.id,
            candidate_id=candidate_id,
        )
    except retention_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        ) from exc
