"""Data retention — on-demand hard delete + TTL helper (Constitution Principle VI).

Hard-deletes a candidate and ALL linked personal data (document, consent, score, dossier,
decisions) so nothing remains accessible afterwards. Deletion is explicit (not relying on DB
FK cascades, so it behaves identically on SQLite and Postgres). The immutable audit log records
the deletion WITHOUT any PII (only non-identifying flags/counts).

The TTL helper finds/deletes candidates older than `CANDIDATE_DATA_TTL_DAYS`. No scheduler is
wired in this phase; the helper is callable and tested.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit_log import AuditEvent
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument
from app.models.consent import Consent
from app.models.decision import Decision
from app.models.dossier import Dossier
from app.models.score import Score
from app.services import audit_service


class NotFoundError(Exception):
    """Candidate not found within the caller's organization."""


def _rowcount(result: object) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


async def _purge_candidate_rows(db: AsyncSession, *, candidate_id: uuid.UUID) -> dict:
    """Delete all child rows for a candidate; return non-PII counts for the audit meta."""
    dec = await db.execute(delete(Decision).where(Decision.candidate_id == candidate_id))
    sco = await db.execute(delete(Score).where(Score.candidate_id == candidate_id))
    dos = await db.execute(delete(Dossier).where(Dossier.candidate_id == candidate_id))
    con = await db.execute(delete(Consent).where(Consent.candidate_id == candidate_id))
    doc = await db.execute(
        delete(CandidateDocument).where(CandidateDocument.candidate_id == candidate_id)
    )
    await db.execute(delete(Candidate).where(Candidate.id == candidate_id))
    return {
        "documents_deleted": _rowcount(doc),
        "consents_deleted": _rowcount(con),
        "scores_deleted": _rowcount(sco),
        "dossiers_deleted": _rowcount(dos),
        "decisions_deleted": _rowcount(dec),
    }


async def delete_candidate(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    candidate_id: uuid.UUID,
    reason: str = "user_request",
) -> None:
    candidate = await db.get(Candidate, candidate_id)
    if candidate is None or candidate.organization_id != organization_id:
        raise NotFoundError("Candidate not found")

    counts = await _purge_candidate_rows(db, candidate_id=candidate_id)

    # Audit WITHOUT PII: only the candidate id (already non-secret), counts and the reason.
    await audit_service.record(
        db,
        event=AuditEvent.candidate_deleted,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        target_type="candidate",
        target_id=candidate_id,
        meta={"reason": reason, **counts},
    )
    await db.commit()


async def find_expired_candidates(
    db: AsyncSession, *, now: datetime | None = None
) -> list[Candidate]:
    """Candidates whose `created_at` is older than the configured TTL."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=settings.candidate_data_ttl_days)
    rows = await db.scalars(select(Candidate).where(Candidate.created_at < cutoff))
    return list(rows)


async def delete_expired_candidates(
    db: AsyncSession, *, now: datetime | None = None
) -> int:
    """Hard-delete every expired candidate (system reason). Returns the number deleted."""
    expired = await find_expired_candidates(db, now=now)
    for candidate in expired:
        await delete_candidate(
            db,
            organization_id=candidate.organization_id,
            actor_user_id=None,
            candidate_id=candidate.id,
            reason="ttl_expired",
        )
    return len(expired)
