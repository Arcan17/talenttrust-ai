"""Phase 4b-ii — AI Candidate Dossier: assembly, evidence guardrail, neutral inconsistencies."""
from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditEvent, AuditLog
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument, DocumentType
from app.models.user import Role, User
from tests.cv_fixtures import make_pdf

PDF_MIME = "application/pdf"
CONSENT = {"consent_version": "v1", "consent_scope": "professional-evaluation"}

STRONG_CV = (
    "Senior Software Engineer. Experience building APIs with Python, FastAPI, Docker and "
    "PostgreSQL over 6 years. Email: dev@example.org"
)
PY_ONLY_CV = "Engineer. Some experience with Python scripting."

ACCUSATORY = ("miente", "fraude", "falso", "engaño", "lie", "fake", "sospech")
NEUTRAL_MARKERS = (
    "requiere revisión",
    "no se encontró evidencia suficiente",
    "conviene validar en entrevista",
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


async def _vacancy(client, token, *, salary=False, english=False):
    payload = {
        "title": "Python Backend Developer",
        "description": "Build APIs" + (" with English communication" if english else ""),
        "required_skills": ["python", "fastapi"],
        "desired_skills": ["docker"],
        "modality": "remote",
        "country": "CL",
        "seniority": "senior",
    }
    if salary:
        payload["salary_min"] = 1500
        payload["salary_max"] = 2500
    resp = await client.post("/api/v1/vacancies", json=payload, headers=_auth(token))
    assert resp.status_code == 201
    return resp.json()["id"]


async def _upload(client, token, vid, cv=STRONG_CV):
    files = {"file": ("cv.pdf", make_pdf(cv), PDF_MIME)}
    resp = await client.post(
        f"/api/v1/vacancies/{vid}/candidates", files=files, data=CONSENT, headers=_auth(token)
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_generate_dossier_success(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)

    resp = await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "analyzed"
    assert body["summary"]["score"] >= 0
    assert body["recommendation"] in {
        "high_priority_interview", "good_review_gaps", "needs_human_review", "low_fit",
    }
    assert isinstance(body["skills"], list)
    assert isinstance(body["interview_questions"], list)


async def test_get_dossier_returns_existing(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)
    await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))

    got = await client.get(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["candidate_id"] == cid


async def test_dossier_without_consent_409(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    owner = await db_session.scalar(select(User).where(User.email == "admin@acme.com"))
    candidate = Candidate(organization_id=owner.organization_id, vacancy_id=uuid.UUID(vid))
    db_session.add(candidate)
    await db_session.flush()
    db_session.add(
        CandidateDocument(
            organization_id=owner.organization_id,
            candidate_id=candidate.id,
            filename="cv.pdf",
            content_type=DocumentType.pdf,
            size_bytes=10,
            sha256=hashlib.sha256(b"x").hexdigest(),
            raw_text="Python FastAPI developer",
            parsed={"skills": ["python", "fastapi"], "language": "en", "char_count": 24},
        )
    )
    await db_session.commit()
    resp = await client.post(
        f"/api/v1/candidates/{candidate.id}/dossier", headers=_auth(token)
    )
    assert resp.status_code == 409


async def test_dossier_cross_org_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    vid = await _vacancy(client, token_a)
    cid = await _upload(client, token_a, vid)
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token_b))
    assert resp.status_code == 404


async def test_dossier_unauthenticated_401(client):
    resp = await client.post(f"/api/v1/candidates/{uuid.uuid4()}/dossier")
    assert resp.status_code == 401


async def test_viewer_cannot_generate_dossier(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)
    owner = await db_session.scalar(select(User).where(User.email == "admin@acme.com"))
    viewer = User(
        organization_id=owner.organization_id,
        email="viewer@acme.com",
        hashed_password=hash_password("supersecret1"),
        role=Role.viewer,
    )
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    vtoken = create_access_token(viewer.id, viewer.organization_id, viewer.role.value)
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(vtoken))
    assert resp.status_code == 403


async def test_audit_dossier_generated(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)
    await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))
    events = (await db_session.scalars(select(AuditLog.event))).all()
    assert AuditEvent.dossier_generated in events


async def test_candidate_marked_analyzed(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)
    await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))
    cand = await client.get(f"/api/v1/candidates/{cid}", headers=_auth(token))
    assert cand.json()["status"] == "analyzed"


async def test_inconsistencies_use_neutral_language(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token, salary=True, english=True)
    cid = await _upload(client, token, vid, cv=PY_ONLY_CV)
    body = (await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))).json()

    inconsistencies = body["inconsistencies"]
    assert inconsistencies, "expected at least one inconsistency for a weak CV"
    for item in inconsistencies:
        msg = item["message"].lower()
        assert any(n in msg for n in NEUTRAL_MARKERS)
        assert not any(bad in msg for bad in ACCUSATORY)
        assert item["evidence"], "every inconsistency must cite evidence"


async def test_every_conclusion_has_evidence(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token, salary=True)
    cid = await _upload(client, token, vid, cv=PY_ONLY_CV)
    body = (await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))).json()

    for section in ("skills", "gaps", "inconsistencies"):
        for item in body[section]:
            assert item["evidence"], f"{section} item without evidence (no fabrication allowed)"
    valid_sources = {"cv", "vacancy", "score_breakdown", "system_rule"}
    for item in body["skills"]:
        for ev in item["evidence"]:
            assert ev["source"] in valid_sources


async def test_interview_questions_grounded_in_gaps(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid, cv=PY_ONLY_CV)  # missing 'fastapi'
    body = (await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))).json()

    gaps = {g["requirement"] for g in body["gaps"]}
    assert "fastapi" in gaps
    questions = body["interview_questions"]
    assert questions
    assert any(q["based_on"] == "gap" for q in questions)
    for q in questions:
        assert q["evidence"]
        assert q["based_on"] in {"gap", "inconsistency", "skill"}
    # A gap question must reference the actual missing skill (no fabricated skills).
    assert any("fastapi" in q["question"].lower() for q in questions)


async def test_dossier_idempotent_and_reproducible(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)
    first = (await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))).json()
    second = (await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))).json()
    assert first["summary"]["score"] == second["summary"]["score"]
    assert first["recommendation"] == second["recommendation"]

    score = await client.get(f"/api/v1/candidates/{cid}/score", headers=_auth(token))
    assert score.json()["value"] == first["summary"]["score"]
