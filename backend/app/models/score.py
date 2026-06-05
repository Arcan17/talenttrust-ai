"""Score — the deterministic 0–100 candidate↔vacancy fit with an explainable breakdown.

The numeric `value` is computed by the deterministic scoring engine and is NEVER produced
or altered by an LLM (Constitution Principle IV). `breakdown` persists the per-factor
weights and sub-scores; its weighted components reconcile to `value`. `narrative` holds the
LLM-written explanation (added in Phase 4b-ii) which never changes the number.

`recommendation` is non-binding (Principle IX) — it never says "reject"; a human records the
final decision in a later phase.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base, TimestampMixin, UUIDMixin

JSONType = JSON().with_variant(JSONB(), "postgresql")


class Recommendation(enum.StrEnum):
    high_priority_interview = "high_priority_interview"
    good_review_gaps = "good_review_gaps"
    needs_human_review = "needs_human_review"
    low_fit = "low_fit"


class Score(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scores"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)  # 0–100
    recommendation: Mapped[Recommendation] = mapped_column(
        SAEnum(Recommendation, name="score_recommendation"), nullable=False
    )
    # breakdown: list[{factor, weight, sub_score, weighted}] reconciling to `value`.
    breakdown: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    # narrative: LLM explanation (never alters the number); populated in Phase 4b-ii.
    narrative: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
