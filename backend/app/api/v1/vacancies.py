"""Vacancy endpoints — org-scoped CRUD (US1).

Write access: org_admin and recruiter. Read access: any authenticated org member
(including viewer). Cross-organization access yields 404 (Principle VIII).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.vacancy import VacancyCreate, VacancyOut
from app.services import vacancy_service

router = APIRouter(prefix="/vacancies", tags=["vacancies"])

_writer = require_role(Role.org_admin, Role.recruiter)


@router.post("", response_model=VacancyOut, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    body: VacancyCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_writer),
) -> VacancyOut:
    vacancy = await vacancy_service.create_vacancy(
        db, organization_id=current.organization_id, data=body
    )
    return VacancyOut.model_validate(vacancy)


@router.get("", response_model=list[VacancyOut])
async def list_vacancies(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[VacancyOut]:
    vacancies = await vacancy_service.list_vacancies(
        db, organization_id=current.organization_id
    )
    return [VacancyOut.model_validate(v) for v in vacancies]


@router.get("/{vacancy_id}", response_model=VacancyOut)
async def get_vacancy(
    vacancy_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
) -> VacancyOut:
    try:
        vacancy = await vacancy_service.get_vacancy(
            db, organization_id=current.organization_id, vacancy_id=vacancy_id
        )
    except vacancy_service.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found"
        ) from exc
    return VacancyOut.model_validate(vacancy)
