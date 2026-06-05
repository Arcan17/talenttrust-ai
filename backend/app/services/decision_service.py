"""Human decision (HITL) business logic.

A decision is recorded ONLY on explicit human request (Constitution Principle IX). It requires
an existing dossier (for traceability in the MVP) and captures the AI recommendation shown at
that moment as non-binding context — never as the decision itself. The human outcome may differ
from the AI recommendation (e.g. a human `reject`, which the AI never recommends).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditEvent
from app.models.candidate import Candidate
from app.models.decision import Decision, DecisionOutcome
from app.models.dossier import Dossier
from app.services import audit_service


class NotFoundError(Exception):
    """Candidate/decision not found within the caller's organization."""


class DossierRequiredError(Exception):
    """A dossier must exist before a decision can be recorded (MVP traceability)."""


async def record_decision(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    candidate_id: uuid.UUID,
    human_outcome: DecisionOutcome,
    note: str | None,
) -> Decision:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")

    dossier = await db.scalar(select(Dossier).where(Dossier.candidate_id == candidate_id))
    if dossier is None:
        raise DossierRequiredError("A dossier is required before recording a decision")

    decision = Decision(
        organization_id=organization_id,
        candidate_id=candidate_id,
        actor_user_id=actor_user_id,
        human_outcome=human_outcome,
        ai_recommendation=dossier.recommendation,  # non-binding context
        note=note,
    )
    db.add(decision)

    await audit_service.record(
        db,
        event=AuditEvent.decision_recorded,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type="candidate",
        target_id=candidate_id,
        meta={
            "human_outcome": human_outcome.value,
            "ai_recommendation": dossier.recommendation.value,
        },
    )

    await db.commit()
    await db.refresh(decision)
    return decision


async def get_latest_decision(
    db: AsyncSession, *, organization_id: uuid.UUID, candidate_id: uuid.UUID
) -> Decision:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")
    decision = await db.scalar(
        select(Decision)
        .where(Decision.candidate_id == candidate_id)
        .order_by(Decision.decided_at.desc(), Decision.created_at.desc())
    )
    if decision is None:
        raise NotFoundError("Decision not found")
    return decision
