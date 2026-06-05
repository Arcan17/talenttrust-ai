"""Centralized scoring weights and recommendation thresholds.

The six fixed factor weights MUST sum to 100 (Constitution Principle IV/V). They are the
single source of truth for the breakdown; tests assert the sum and the reconciliation of
the weighted components to the final 0–100 value.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.score import Recommendation

# Factor keys — single source of truth for breakdown factor names.
SKILLS = "skills_match"
EXPERIENCE = "experience_relevant"
SENIORITY = "seniority_match"
MODALITY_LOCATION = "modality_location"
EVIDENCE = "evidence_support"
INCONSISTENCY = "inconsistency_penalty"


@dataclass(frozen=True)
class Weights:
    skills: float = 35.0
    experience: float = 20.0
    seniority: float = 15.0
    modality_location: float = 10.0
    evidence: float = 10.0
    inconsistency: float = 10.0

    def as_dict(self) -> dict[str, float]:
        return {
            SKILLS: self.skills,
            EXPERIENCE: self.experience,
            SENIORITY: self.seniority,
            MODALITY_LOCATION: self.modality_location,
            EVIDENCE: self.evidence,
            INCONSISTENCY: self.inconsistency,
        }

    @property
    def total(self) -> float:
        return (
            self.skills
            + self.experience
            + self.seniority
            + self.modality_location
            + self.evidence
            + self.inconsistency
        )


def get_weights() -> Weights:
    return Weights()


# Recommendation thresholds on the 0–100 scale. Never "reject" — recommendations are
# non-binding (Constitution Principle IX). A human records the final decision (Phase 6).
RECOMMEND_HIGH_MIN = 80.0
RECOMMEND_GOOD_MIN = 60.0
RECOMMEND_REVIEW_MIN = 40.0


def recommendation_for(value: float) -> Recommendation:
    """Deterministic, non-binding recommendation from the 0–100 score."""
    if value >= RECOMMEND_HIGH_MIN:
        return Recommendation.high_priority_interview
    if value >= RECOMMEND_GOOD_MIN:
        return Recommendation.good_review_gaps
    if value >= RECOMMEND_REVIEW_MIN:
        return Recommendation.needs_human_review
    return Recommendation.low_fit
