"""Decision — the human-recorded final outcome for a candidate (HITL).

Created ONLY by an explicit human action (Constitution Principle IX): the system never writes
a final outcome automatically. Each row captures the human outcome AND the AI recommendation
shown at the time (as non-binding context) — the AI recommendation never replaces the human
decision. A human may choose `reject` even though the AI recommendation is never "reject".
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.score import Recommendation


class DecisionOutcome(enum.StrEnum):
    interview = "interview"
    review = "review"
    reject = "reject"
    hold = "hold"


class Decision(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    human_outcome: Mapped[DecisionOutcome] = mapped_column(
        SAEnum(DecisionOutcome, name="decision_outcome"), nullable=False
    )
    # The AI recommendation shown at decision time — stored as non-binding context only.
    ai_recommendation: Mapped[Recommendation] = mapped_column(
        SAEnum(Recommendation, name="score_recommendation"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
