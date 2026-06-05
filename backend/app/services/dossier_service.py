"""Dossier assembly — the AI Candidate Dossier (Phase 4b-ii).

Reuses the deterministic Score, adds skills-with-evidence, gaps, neutral inconsistencies and
grounded interview questions, and a non-binding recommendation. Enforces the no-fabrication
guardrail: every skill/gap/inconsistency MUST carry at least one evidence reference
(Constitution Principle I). Emits `dossier_generated` and marks the candidate `analyzed`.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEvent
from app.models.candidate import Candidate, CandidateStatus
from app.models.candidate_document import CandidateDocument
from app.models.dossier import Dossier
from app.models.vacancy import Vacancy
from app.providers.factory import get_llm_provider
from app.schemas.dossier import DossierOut
from app.scoring import fairness_guard, inconsistency_detector
from app.services import audit_service, candidate_service, interview_questions, scoring_service


class NotFoundError(Exception):
    """Candidate/vacancy/dossier not found within the caller's organization."""


class ConsentRequiredError(Exception):
    """No valid consent exists for this candidate."""


def _norm(items: list[str]) -> set[str]:
    return {s.strip().lower() for s in items if s and s.strip()}


def _ev(source: str, detail: str) -> dict:
    return {"source": source, "detail": detail}


def _has_evidence(item: dict) -> bool:
    return bool(item.get("evidence"))


def _build_skills(vacancy: Vacancy, candidate_skills: list[str]) -> list[dict]:
    required = _norm(vacancy.required_skills)
    desired = _norm(vacancy.desired_skills)
    out: list[dict] = []
    for skill in candidate_skills:
        low = skill.strip().lower()
        if not low:
            continue
        is_required = low in required
        evidence = [_ev("cv", "Mencionada en el CV")]
        if is_required or low in desired:
            evidence.append(_ev("vacancy", "Listada en la vacante"))
            evidence.append(_ev("score_breakdown", "Aporta al factor de skills"))
        out.append({"name": skill, "required": is_required, "evidence": evidence})
    return out


def _build_gaps(vacancy: Vacancy, candidate_skills: list[str]) -> list[dict]:
    missing = sorted(_norm(vacancy.required_skills) - _norm(candidate_skills))
    return [
        {
            "requirement": skill,
            "note": "Skill obligatoria no evidenciada en el CV; conviene validar en entrevista.",
            "evidence": [
                _ev("vacancy", f"Skill obligatoria: {skill}"),
                _ev("cv", "No detectada en el documento"),
            ],
        }
        for skill in missing
    ]


async def _summary_text(value: int, recommendation: str, present: list[str]) -> str:
    context = (
        f"score={value}/100; recommendation={recommendation}; "
        f"skills_present={', '.join(present) or 'none'}"
    )
    result = await get_llm_provider().complete(
        "Summarize the candidate fit for a recruiter in one neutral sentence.",
        system="You explain an already-computed evaluation; you never assign scores or decide.",
        context=context,
    )
    return result.text


async def generate_dossier(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> DossierOut:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")

    if not await candidate_service.has_consent(db, candidate_id=candidate_id):
        raise ConsentRequiredError("Consent is required before analysis")

    document = await db.scalar(
        select(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)
    )
    if document is None:
        raise NotFoundError("Candidate has no document")

    vacancy = await db.get(Vacancy, candidate.vacancy_id)
    if vacancy is None or vacancy.organization_id != organization_id:
        raise NotFoundError("Vacancy not found")

    # Reuse / (idempotently) compute the deterministic score.
    score = await scoring_service.score_candidate(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        candidate_id=candidate_id,
    )

    candidate_skills = list(document.parsed.get("skills", []))
    sanitized_text = fairness_guard.sanitize_text(document.raw_text)
    required = _norm(vacancy.required_skills)
    present_required = sorted(required & _norm(candidate_skills))
    missing_required = sorted(required - _norm(candidate_skills))

    skills = [s for s in _build_skills(vacancy, candidate_skills) if _has_evidence(s)]
    gaps = [g for g in _build_gaps(vacancy, candidate_skills) if _has_evidence(g)]
    inconsistencies = [
        i
        for i in inconsistency_detector.detect(
            vacancy=vacancy,
            parsed=document.parsed,
            sanitized_text=sanitized_text,
            breakdown=score.breakdown,
        )
        if _has_evidence(i)
    ]
    questions = interview_questions.generate(
        missing_required_skills=missing_required,
        present_required_skills=present_required,
        inconsistencies=inconsistencies,
    )
    summary_text = await _summary_text(
        score.value, score.recommendation.value, present_required
    )
    summary = {
        "text": summary_text,
        "score": score.value,
        "recommendation": score.recommendation.value,
        "evidence": [_ev("score_breakdown", "Resumen basado en el score determinístico")],
    }

    dossier = await db.scalar(select(Dossier).where(Dossier.candidate_id == candidate_id))
    if dossier is None:
        dossier = Dossier(
            organization_id=organization_id,
            candidate_id=candidate_id,
            vacancy_id=vacancy.id,
        )
        db.add(dossier)
    dossier.summary = summary
    dossier.summary_text = summary_text
    dossier.skills = skills
    dossier.gaps = gaps
    dossier.inconsistencies = inconsistencies
    dossier.interview_questions = questions
    dossier.recommendation = score.recommendation

    candidate.status = CandidateStatus.analyzed

    await audit_service.record(
        db,
        event=AuditEvent.dossier_generated,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type="candidate",
        target_id=candidate_id,
        meta={"score": score.value, "recommendation": score.recommendation.value},
    )

    await db.commit()
    await db.refresh(dossier)
    await db.refresh(candidate)
    return _to_out(dossier, candidate)


async def get_dossier(
    db: AsyncSession, *, organization_id: uuid.UUID, candidate_id: uuid.UUID
) -> DossierOut:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")
    dossier = await db.scalar(select(Dossier).where(Dossier.candidate_id == candidate_id))
    if dossier is None:
        raise NotFoundError("Dossier not found")
    return _to_out(dossier, candidate)


def _to_out(dossier: Dossier, candidate: Candidate) -> DossierOut:
    return DossierOut.model_validate(
        {
            "id": dossier.id,
            "candidate_id": dossier.candidate_id,
            "vacancy_id": dossier.vacancy_id,
            "status": candidate.status,
            "summary": dossier.summary,
            "skills": dossier.skills,
            "gaps": dossier.gaps,
            "inconsistencies": dossier.inconsistencies,
            "interview_questions": dossier.interview_questions,
            "recommendation": dossier.recommendation,
        }
    )
