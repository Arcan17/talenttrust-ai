"""Vacancy request/response schemas with validation (FR-004, FR-005)."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.vacancy import Modality, Seniority, VacancyStatus


class VacancyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=10_000)
    required_skills: list[str] = Field(min_length=1)
    desired_skills: list[str] = Field(default_factory=list)
    modality: Modality
    country: str | None = Field(default=None, max_length=120)
    salary_min: int | None = Field(default=None, ge=0)
    salary_max: int | None = Field(default=None, ge=0)
    seniority: Seniority

    @field_validator("required_skills", "desired_skills")
    @classmethod
    def _no_blank_skills(cls, v: list[str]) -> list[str]:
        cleaned = [s.strip() for s in v if s and s.strip()]
        return cleaned

    @field_validator("required_skills")
    @classmethod
    def _required_non_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("required_skills must contain at least one non-blank skill")
        return v


class VacancyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    title: str
    description: str
    required_skills: list[str]
    desired_skills: list[str]
    modality: Modality
    country: str | None
    salary_min: int | None
    salary_max: int | None
    seniority: Seniority
    status: VacancyStatus
