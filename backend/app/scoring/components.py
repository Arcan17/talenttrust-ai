"""Deterministic per-factor sub-score functions (each returns a value in [0, 1]).

Pure functions of structured, non-sensitive inputs — no LLM, no randomness, no wall-clock —
so the overall 0–100 score is reproducible (Constitution Principles IV/V). Inputs are an
allowlist of signals: the vacancy's required/desired skills, the candidate's detected skills
(from the parser's vocabulary), and a fairness-sanitized text used only for token presence
checks (seniority, country, skill evidence). Sensitive attributes never reach this module.
"""
from __future__ import annotations

import math

from app.models.vacancy import Modality, Seniority, Vacancy

_SENIORITY_ORDER = {Seniority.junior: 0, Seniority.mid: 1, Seniority.senior: 2}

_SENIORITY_TOKENS = {
    Seniority.senior: ("senior", "lead", "principal", "staff", "sr."),
    Seniority.junior: ("junior", "trainee", "intern", "becario", "practicante", "jr."),
}


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _norm(items: list[str]) -> set[str]:
    return {s.strip().lower() for s in items if s and s.strip()}


def skills_match(required_skills: list[str], candidate_skills: list[str]) -> float:
    """Fraction of required skills present among the candidate's detected skills."""
    required = _norm(required_skills)
    if not required:
        return 0.0
    candidate = _norm(candidate_skills)
    return clamp01(len(required & candidate) / len(required))


def experience_relevant(required_skills: list[str], sanitized_text: str) -> float:
    """Fraction of required skills with textual evidence in the (sanitized) CV body."""
    required = _norm(required_skills)
    if not required:
        return 0.0
    lowered = sanitized_text.lower()
    hits = sum(1 for s in required if s in lowered)
    return clamp01(hits / len(required))


def infer_candidate_seniority(sanitized_text: str) -> Seniority:
    lowered = sanitized_text.lower()
    for level, tokens in _SENIORITY_TOKENS.items():
        if any(tok in lowered for tok in tokens):
            return level
    return Seniority.mid


def seniority_match(vacancy: Vacancy, sanitized_text: str) -> float:
    candidate = infer_candidate_seniority(sanitized_text)
    dist = abs(_SENIORITY_ORDER[vacancy.seniority] - _SENIORITY_ORDER[candidate])
    return {0: 1.0, 1: 0.6}.get(dist, 0.2)


def modality_location(vacancy: Vacancy, sanitized_text: str) -> float:
    modality = 1.0 if vacancy.modality == Modality.remote else 0.6
    location = 0.5
    if vacancy.country and vacancy.country.strip():
        if vacancy.country.strip().lower() in sanitized_text.lower():
            location = 1.0
    return clamp01(0.6 * modality + 0.4 * location)


def evidence_support(
    requirements_embedding: list[float] | None, candidate_skills_embedding: list[float] | None
) -> float:
    """Embedding similarity between the vacancy requirements and candidate skills.

    Uses the (mock by default) embedding provider's vectors — deterministic and offline.
    Computed over skills only (never raw CV text), so sensitive content cannot affect it.
    """
    return clamp01(cosine(requirements_embedding, candidate_skills_embedding))


def inconsistency_penalty() -> float:
    """Retention factor (1.0 = no detected inconsistencies).

    The inconsistency detector lands in Phase 4b-ii; until then this returns 1.0 so the
    factor contributes its full weight and never fabricates a penalty.
    """
    return 1.0
