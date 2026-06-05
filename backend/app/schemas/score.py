"""Score response schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict

from app.models.score import Recommendation


class ScoreBreakdownItem(BaseModel):
    factor: str
    weight: float
    sub_score: float
    weighted: float


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    value: int  # 0–100
    recommendation: Recommendation
    breakdown: list[ScoreBreakdownItem]
    narrative: dict | None = None
