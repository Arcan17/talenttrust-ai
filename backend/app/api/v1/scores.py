"""Score endpoints — compute and read a candidate's deterministic fit score (Phase 4b-i).

This is the scoring step only; the full dossier (summary, inconsistencies, interview
questions) is assembled in Phase 4b-ii. Write role required to compute; any org member may
read. Generating a score without a valid consent returns 409 (FR-009).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.score import ScoreOut
from app.services import scoring_service

router = APIRouter(prefix="/candidates", tags=["scores"])

_writer = require_role(Role.org_admin, Role.recruiter)


@router.post("/{candidate_id}/score", response_model=ScoreOut, status_code=status.HTTP_201_CREATED)
async def compute_score(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_writer),
) -> ScoreOut:
    try:
        score = await scoring_service.score_candidate(
            db,
            organization_id=current.organization_id,
            actor_user_id=current.id,
            candidate_id=candidate_id,
        )
    except scoring_service.ConsentRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except scoring_service.NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except scoring_service.ScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return ScoreOut.model_validate(score)


@router.get("/{candidate_id}/score", response_model=ScoreOut)
async def get_score(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ScoreOut:
    try:
        score = await scoring_service.get_score(
            db, organization_id=current.organization_id, candidate_id=candidate_id
        )
    except scoring_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Score not found"
        ) from exc
    return ScoreOut.model_validate(score)
