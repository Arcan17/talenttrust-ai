"""Phase 7 — retention: on-demand hard delete (cascade), RBAC, PII-free audit, TTL helper."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditEvent, AuditLog
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument
from app.models.consent import Consent
from app.models.decision import Decision
from app.models.dossier import Dossier
from app.models.score import Score
from app.models.user import Role, User
from app.services import retention_service
from tests.cv_fixtures import make_pdf

PDF_MIME = "application/pdf"
CONSENT = {"consent_version": "v1", "consent_scope": "professional-evaluation"}
STRONG_CV = (
    "Senior Software Engineer with Python, FastAPI, Docker and PostgreSQL. 6 years building APIs. "
    "Email: jane@example.org"
)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org, email):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": "supersecret1"},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _vacancy(client, token):
    payload = {
        "title": "Python Backend Developer",
        "description": "APIs",
        "required_skills": ["python", "fastapi"],
        "desired_skills": ["docker"],
        "modality": "remote",
        "country": "CL",
        "seniority": "mid",
    }
    return (await client.post("/api/v1/vacancies", json=payload, headers=_auth(token))).json()["id"]


async def _full_candidate(client, token):
    """Create a candidate with document, consent, score, dossier and a decision."""
    vid = await _vacancy(client, token)
    files = {"file": ("cv.pdf", make_pdf(STRONG_CV), PDF_MIME)}
    up = await client.post(
        f"/api/v1/vacancies/{vid}/candidates",
        files=files,
        data={**CONSENT, "display_name": "Jane Doe"},
        headers=_auth(token),
    )
    cid = up.json()["id"]
    await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))
    await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "interview", "note": "Great"},
        headers=_auth(token),
    )
    return cid


async def _make_user(db_session, owner_email, email, role):
    owner = await db_session.scalar(select(User).where(User.email == owner_email))
    user = User(
        organization_id=owner.organization_id,
        email=email,
        hashed_password=hash_password("supersecret1"),
        role=role,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return create_access_token(user.id, user.organization_id, user.role.value)


async def _count(db_session, model, candidate_id):
    return await db_session.scalar(
        select(func.count()).select_from(model).where(model.candidate_id == candidate_id)
    )


async def test_org_admin_deletes_candidate(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _full_candidate(client, token)
    resp = await client.delete(f"/api/v1/candidates/{cid}", headers=_auth(token))
    assert resp.status_code == 204

    got = await client.get(f"/api/v1/candidates/{cid}", headers=_auth(token))
    assert got.status_code == 404


async def test_delete_cascades_all_linked_data(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = uuid.UUID(await _full_candidate(client, token))

    # Sanity: artifacts exist before deletion.
    assert await db_session.get(Candidate, cid) is not None
    assert await _count(db_session, CandidateDocument, cid) == 1
    assert await _count(db_session, Consent, cid) == 1
    assert await _count(db_session, Score, cid) == 1
    assert await _count(db_session, Dossier, cid) == 1
    assert await _count(db_session, Decision, cid) == 1

    resp = await client.delete(f"/api/v1/candidates/{cid}", headers=_auth(token))
    assert resp.status_code == 204

    db_session.expire_all()
    assert await db_session.get(Candidate, cid) is None
    assert await _count(db_session, CandidateDocument, cid) == 0
    assert await _count(db_session, Consent, cid) == 0
    assert await _count(db_session, Score, cid) == 0
    assert await _count(db_session, Dossier, cid) == 0
    assert await _count(db_session, Decision, cid) == 0


async def test_delete_cross_org_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    cid = await _full_candidate(client, token_a)
    resp = await client.delete(f"/api/v1/candidates/{cid}", headers=_auth(token_b))
    assert resp.status_code == 404


async def test_recruiter_cannot_delete(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _full_candidate(client, token)
    rtoken = await _make_user(db_session, "admin@acme.com", "rec@acme.com", Role.recruiter)
    resp = await client.delete(f"/api/v1/candidates/{cid}", headers=_auth(rtoken))
    assert resp.status_code == 403


async def test_viewer_cannot_delete(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _full_candidate(client, token)
    vtoken = await _make_user(db_session, "admin@acme.com", "viewer@acme.com", Role.viewer)
    resp = await client.delete(f"/api/v1/candidates/{cid}", headers=_auth(vtoken))
    assert resp.status_code == 403


async def test_delete_unauthenticated_401(client):
    resp = await client.delete(f"/api/v1/candidates/{uuid.uuid4()}")
    assert resp.status_code == 401


async def test_delete_audit_recorded_without_pii(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = uuid.UUID(await _full_candidate(client, token))
    await client.delete(f"/api/v1/candidates/{cid}", headers=_auth(token))

    row = await db_session.scalar(
        select(AuditLog).where(AuditLog.event == AuditEvent.candidate_deleted)
    )
    assert row is not None
    assert row.target_id == str(cid)
    meta_str = str(row.meta).lower()
    # No PII in audit metadata.
    assert "jane" not in meta_str
    assert "@" not in meta_str
    assert "example.org" not in meta_str
    assert set(row.meta.keys()) <= {
        "reason", "documents_deleted", "consents_deleted", "scores_deleted",
        "dossiers_deleted", "decisions_deleted",
    }


async def test_ttl_finds_and_deletes_expired(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = uuid.UUID(await _vacancy(client, token))
    owner = await db_session.scalar(select(User).where(User.email == "admin@acme.com"))
    now = datetime.now(UTC)

    old = Candidate(
        organization_id=owner.organization_id,
        vacancy_id=vid,
        created_at=now - timedelta(days=200),  # older than the 180-day TTL
    )
    recent = Candidate(
        organization_id=owner.organization_id,
        vacancy_id=vid,
        created_at=now - timedelta(days=5),
    )
    db_session.add_all([old, recent])
    await db_session.commit()
    old_id, recent_id = old.id, recent.id

    expired = await retention_service.find_expired_candidates(db_session, now=now)
    assert old_id in {c.id for c in expired}
    assert recent_id not in {c.id for c in expired}

    deleted = await retention_service.delete_expired_candidates(db_session, now=now)
    assert deleted == 1
    db_session.expire_all()
    assert await db_session.get(Candidate, old_id) is None
    assert await db_session.get(Candidate, recent_id) is not None
