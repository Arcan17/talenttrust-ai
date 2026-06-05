"""Decision endpoints — record/read the human final decision (HITL, US3).

Write role (org_admin/recruiter) records; any org member may read. A decision requires an
existing dossier (409 otherwise). The system never decides automatically — a decision exists
only after this explicit human call.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.decision import DecisionCreate, DecisionOut
from app.services import decision_service

router = APIRouter(prefix="/candidates", tags=["decisions"])

_writer = require_role(Role.org_admin, Role.recruiter)


@router.post(
    "/{candidate_id}/decision", response_model=DecisionOut, status_code=status.HTTP_201_CREATED
)
async def record_decision(
    candidate_id: uuid.UUID,
    body: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_writer),
) -> DecisionOut:
    try:
        decision = await decision_service.record_decision(
            db,
            organization_id=current.organization_id,
            actor_user_id=current.id,
            candidate_id=candidate_id,
            human_outcome=body.human_outcome,
            note=body.note,
        )
    except decision_service.DossierRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except decision_service.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DecisionOut.model_validate(decision)


@router.get("/{candidate_id}/decision", response_model=DecisionOut)
async def get_decision(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> DecisionOut:
    try:
        decision = await decision_service.get_latest_decision(
            db, organization_id=current.organization_id, candidate_id=candidate_id
        )
    except decision_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        ) from exc
    return DecisionOut.model_validate(decision)
