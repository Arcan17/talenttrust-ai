"""Candidate↔vacancy scoring engine.

The 0–100 `value` is a weighted sum of deterministic per-factor sub-scores (Constitution
Principles IV/V). The LLM (mock by default) is used ONLY to phrase a narrative and MUST NOT
change the number. Embeddings (mock by default) are deterministic, so the same candidate +
vacancy yields the same score. Sensitive attributes are stripped by the fairness guard before
any text is inspected.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEvent
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument
from app.models.score import Recommendation, Score
from app.models.vacancy import Vacancy
from app.providers.factory import get_embedding_provider, get_llm_provider
from app.scoring import components as C
from app.scoring import fairness_guard
from app.scoring import weights as W
from app.services import audit_service, candidate_service


class NotFoundError(Exception):
    """Candidate/vacancy not found within the caller's organization."""


class ConsentRequiredError(Exception):
    """No valid consent exists for this candidate (analysis is blocked)."""


class ScoringError(Exception):
    """The candidate cannot be scored (e.g. no document)."""


def _round(x: float) -> float:
    return float(round(float(x), 4))


def compute_score(
    *,
    vacancy: Vacancy,
    candidate_skills: list[str],
    candidate_skills_embedding: list[float] | None,
    requirements_embedding: list[float] | None,
    sanitized_text: str,
) -> tuple[int, list[dict], Recommendation]:
    """Pure, deterministic 0–100 score + breakdown. No DB, no LLM, no randomness."""
    weights = W.get_weights().as_dict()
    subscores = {
        W.SKILLS: C.skills_match(vacancy.required_skills, candidate_skills),
        W.EXPERIENCE: C.experience_relevant(vacancy.required_skills, sanitized_text),
        W.SENIORITY: C.seniority_match(vacancy, sanitized_text),
        W.MODALITY_LOCATION: C.modality_location(vacancy, sanitized_text),
        W.EVIDENCE: C.evidence_support(requirements_embedding, candidate_skills_embedding),
        W.INCONSISTENCY: C.inconsistency_penalty(),
    }
    breakdown: list[dict] = []
    weighted_total = 0.0
    for factor, weight in weights.items():
        sub = subscores[factor]
        weighted = weight * sub
        weighted_total += weighted
        breakdown.append(
            {
                "factor": factor,
                "weight": weight,
                "sub_score": _round(sub),
                "weighted": _round(weighted),
            }
        )
    value = max(0, min(100, int(round(weighted_total))))
    return value, breakdown, W.recommendation_for(value)


async def _embed_one(text: str) -> list[float]:
    vectors = await get_embedding_provider().embed([text])
    return vectors[0]


async def _narrative(value: int, breakdown: list[dict], recommendation: Recommendation) -> dict:
    """LLM explanation of an already-computed score. Never alters the number."""
    top = sorted(breakdown, key=lambda b: b["weighted"], reverse=True)[:3]
    context = "; ".join(f"{b['factor']}={b['sub_score']}" for b in top)
    result = await get_llm_provider().complete(
        "Explain a candidate fit score to a recruiter in one sentence.",
        system="You explain an already-computed score; you never assign or change scores.",
        context=context,
    )
    return {
        "rationale": result.text,
        "recommendation": recommendation.value,
        "top_factors": [b["factor"] for b in top],
        "model": result.model,
    }


async def score_candidate(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> Score:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")

    if not await candidate_service.has_consent(db, candidate_id=candidate_id):
        raise ConsentRequiredError("Consent is required before analysis")

    document = await db.scalar(
        select(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)
    )
    if document is None:
        raise ScoringError("Candidate has no document to score")

    vacancy = await db.get(Vacancy, candidate.vacancy_id)
    if vacancy is None or vacancy.organization_id != organization_id:
        raise NotFoundError("Vacancy not found")

    # Populate the vacancy requirements embedding once (deterministic mock by default).
    if vacancy.requirements_embedding is None:
        req_text = " ".join([*vacancy.required_skills, *vacancy.desired_skills]) or vacancy.title
        vacancy.requirements_embedding = await _embed_one(req_text)

    candidate_skills = list(document.parsed.get("skills", []))
    candidate_skills_embedding = await _embed_one(" ".join(candidate_skills) or "none")
    sanitized_text = fairness_guard.sanitize_text(document.raw_text)

    value, breakdown, recommendation = compute_score(
        vacancy=vacancy,
        candidate_skills=candidate_skills,
        candidate_skills_embedding=candidate_skills_embedding,
        requirements_embedding=vacancy.requirements_embedding,
        sanitized_text=sanitized_text,
    )
    narrative = await _narrative(value, breakdown, recommendation)

    score = await db.scalar(select(Score).where(Score.candidate_id == candidate_id))
    if score is None:
        score = Score(organization_id=organization_id, candidate_id=candidate_id)
        db.add(score)
    score.value = value
    score.recommendation = recommendation
    score.breakdown = breakdown
    score.narrative = narrative

    await audit_service.record(
        db,
        event=AuditEvent.score_computed,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type="candidate",
        target_id=candidate_id,
        meta={"value": value, "recommendation": recommendation.value},
    )

    await db.commit()
    await db.refresh(score)
    return score


async def get_score(
    db: AsyncSession, *, organization_id: uuid.UUID, candidate_id: uuid.UUID
) -> Score:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")
    score = await db.scalar(select(Score).where(Score.candidate_id == candidate_id))
    if score is None:
        raise NotFoundError("Score not found")
    return score
