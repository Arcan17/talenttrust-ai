"""Phase 5 — human decision (HITL): recording, RBAC, isolation, audit, non-binding AI rec."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditEvent, AuditLog
from app.models.user import Role, User
from tests.cv_fixtures import make_pdf

PDF_MIME = "application/pdf"
CONSENT = {"consent_version": "v1", "consent_scope": "professional-evaluation"}
STRONG_CV = (
    "Senior Software Engineer with Python, FastAPI, Docker and PostgreSQL. 6 years building APIs."
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
    resp = await client.post("/api/v1/vacancies", json=payload, headers=_auth(token))
    return resp.json()["id"]


async def _candidate_with_dossier(client, token, cv=STRONG_CV):
    vid = await _vacancy(client, token)
    files = {"file": ("cv.pdf", make_pdf(cv), PDF_MIME)}
    up = await client.post(
        f"/api/v1/vacancies/{vid}/candidates", files=files, data=CONSENT, headers=_auth(token)
    )
    cid = up.json()["id"]
    dres = await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))
    assert dres.status_code == 201
    return cid, dres.json()["recommendation"]


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


async def test_record_decision_success(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, ai_rec = await _candidate_with_dossier(client, token)
    resp = await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "interview", "note": "Strong fit"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["human_outcome"] == "interview"
    assert body["ai_recommendation"] == ai_rec
    assert body["note"] == "Strong fit"
    assert body["decided_at"]


async def test_get_decision_returns_existing(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, _ = await _candidate_with_dossier(client, token)
    await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "review"},
        headers=_auth(token),
    )
    got = await client.get(f"/api/v1/candidates/{cid}/decision", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["human_outcome"] == "review"


async def test_audit_decision_recorded(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, _ = await _candidate_with_dossier(client, token)
    await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "hold"},
        headers=_auth(token),
    )
    events = (await db_session.scalars(select(AuditLog.event))).all()
    assert AuditEvent.decision_recorded in events


async def test_decision_cross_org_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    cid, _ = await _candidate_with_dossier(client, token_a)
    resp = await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "interview"},
        headers=_auth(token_b),
    )
    assert resp.status_code == 404
    get = await client.get(f"/api/v1/candidates/{cid}/decision", headers=_auth(token_b))
    assert get.status_code == 404


async def test_decision_unauthenticated_401(client):
    resp = await client.post(
        f"/api/v1/candidates/{uuid.uuid4()}/decision",
        json={"human_outcome": "interview"},
    )
    assert resp.status_code == 401


async def test_viewer_cannot_record_decision(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, _ = await _candidate_with_dossier(client, token)
    vtoken = await _make_user(db_session, "admin@acme.com", "viewer@acme.com", Role.viewer)
    resp = await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "interview"},
        headers=_auth(vtoken),
    )
    assert resp.status_code == 403


async def test_recruiter_can_record_decision(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, _ = await _candidate_with_dossier(client, token)
    rtoken = await _make_user(db_session, "admin@acme.com", "rec@acme.com", Role.recruiter)
    resp = await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "review"},
        headers=_auth(rtoken),
    )
    assert resp.status_code == 201


async def test_invalid_decision_is_422(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, _ = await _candidate_with_dossier(client, token)
    resp = await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "banana"},
        headers=_auth(token),
    )
    assert resp.status_code == 422


async def test_no_automatic_decision(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, _ = await _candidate_with_dossier(client, token)
    # No decision was recorded by a human → none exists.
    got = await client.get(f"/api/v1/candidates/{cid}/decision", headers=_auth(token))
    assert got.status_code == 404


async def test_human_decision_may_differ_from_ai_recommendation(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid, ai_rec = await _candidate_with_dossier(client, token)
    # AI never recommends "reject"; a human still may decide it.
    resp = await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "reject", "note": "Team fit concerns"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["human_outcome"] == "reject"
    assert body["ai_recommendation"] == ai_rec
    assert body["ai_recommendation"] != "reject"  # AI recommendation space never contains reject
    assert body["human_outcome"] != body["ai_recommendation"]


async def test_decision_requires_dossier(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    files = {"file": ("cv.pdf", make_pdf(STRONG_CV), PDF_MIME)}
    up = await client.post(
        f"/api/v1/vacancies/{vid}/candidates", files=files, data=CONSENT, headers=_auth(token)
    )
    cid = up.json()["id"]
    # No dossier generated yet → recording a decision is blocked (409).
    resp = await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "interview"},
        headers=_auth(token),
    )
    assert resp.status_code == 409
