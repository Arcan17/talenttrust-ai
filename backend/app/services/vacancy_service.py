"""Vacancy business logic — strictly organization-scoped (Constitution Principle VIII).

Every query filters by the caller's organization_id; a vacancy belonging to another
organization is indistinguishable from a missing one (NotFound), preventing cross-tenant
leakage.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vacancy import Vacancy
from app.schemas.vacancy import VacancyCreate


class NotFoundError(Exception):
    """Raised when a vacancy does not exist within the caller's organization."""


async def create_vacancy(
    db: AsyncSession, *, organization_id: uuid.UUID, data: VacancyCreate
) -> Vacancy:
    vacancy = Vacancy(
        organization_id=organization_id,
        title=data.title,
        description=data.description,
        required_skills=data.required_skills,
        desired_skills=data.desired_skills,
        modality=data.modality,
        country=data.country,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        seniority=data.seniority,
    )
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)
    return vacancy


async def list_vacancies(
    db: AsyncSession, *, organization_id: uuid.UUID
) -> list[Vacancy]:
    rows = await db.scalars(
        select(Vacancy)
        .where(Vacancy.organization_id == organization_id)
        .order_by(Vacancy.created_at.desc())
    )
    return list(rows)


async def get_vacancy(
    db: AsyncSession, *, organization_id: uuid.UUID, vacancy_id: uuid.UUID
) -> Vacancy:
    vacancy = await db.get(Vacancy, vacancy_id)
    if vacancy is None or vacancy.organization_id != organization_id:
        raise NotFoundError("Vacancy not found")
    return vacancy
