"""Dossier endpoints — generate and read the AI Candidate Dossier (Phase 4b-ii).

Write role (org_admin/recruiter) generates; any org member may read. Generating without a
valid consent returns 409 (FR-009). The recommendation is non-binding; a human records the
final decision in a later phase.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.dossier import DossierOut
from app.services import dossier_service

router = APIRouter(prefix="/candidates", tags=["dossiers"])

_writer = require_role(Role.org_admin, Role.recruiter)


@router.post(
    "/{candidate_id}/dossier", response_model=DossierOut, status_code=status.HTTP_201_CREATED
)
async def generate_dossier(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_writer),
) -> DossierOut:
    try:
        return await dossier_service.generate_dossier(
            db,
            organization_id=current.organization_id,
            actor_user_id=current.id,
            candidate_id=candidate_id,
        )
    except dossier_service.ConsentRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except dossier_service.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{candidate_id}/dossier", response_model=DossierOut)
async def get_dossier(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> DossierOut:
    try:
        return await dossier_service.get_dossier(
            db, organization_id=current.organization_id, candidate_id=candidate_id
        )
    except dossier_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dossier not found"
        ) from exc
