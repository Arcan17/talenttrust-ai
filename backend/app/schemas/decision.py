"""Decision request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.decision import DecisionOutcome
from app.models.score import Recommendation


class DecisionCreate(BaseModel):
    human_outcome: DecisionOutcome
    note: str | None = Field(default=None, max_length=2000)


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    candidate_id: uuid.UUID
    organization_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    human_outcome: DecisionOutcome
    ai_recommendation: Recommendation  # non-binding context shown at decision time
    note: str | None
    decided_at: datetime
