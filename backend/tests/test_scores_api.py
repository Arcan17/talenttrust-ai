"""Phase 4b-i — scoring endpoint + service: consent gate, isolation, audit, LLM independence."""
from __future__ import annotations

import hashlib
import uuid

from sqlalchemy import select

from app.models.audit_log import AuditEvent, AuditLog
from app.models.candidate import Candidate
from app.models.candidate_document import CandidateDocument, DocumentType
from app.models.user import User
from app.providers.base import LLMResult
from app.services import scoring_service
from tests.cv_fixtures import ENGLISH_CV, make_pdf

VACANCY = {
    "title": "Python Backend Developer",
    "description": "APIs",
    "required_skills": ["python", "fastapi"],
    "desired_skills": ["docker"],
    "modality": "remote",
    "country": "CL",
    "seniority": "mid",
}
CONSENT = {"consent_version": "v1", "consent_scope": "professional-evaluation"}
PDF_MIME = "application/pdf"


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
    resp = await client.post("/api/v1/vacancies", json=VACANCY, headers=_auth(token))
    return resp.json()["id"]


async def _upload(client, token, vid):
    files = {"file": ("cv.pdf", make_pdf(ENGLISH_CV), PDF_MIME)}
    resp = await client.post(
        f"/api/v1/vacancies/{vid}/candidates", files=files, data=CONSENT, headers=_auth(token)
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_compute_and_get_score(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)

    resp = await client.post(f"/api/v1/candidates/{cid}/score", headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert 0 <= body["value"] <= 100
    assert body["recommendation"] in {
        "high_priority_interview", "good_review_gaps", "needs_human_review", "low_fit",
    }
    assert len(body["breakdown"]) == 6
    weighted = sum(item["weighted"] for item in body["breakdown"])
    assert abs(weighted - body["value"]) <= 0.5

    got = await client.get(f"/api/v1/candidates/{cid}/score", headers=_auth(token))
    assert got.status_code == 200
    assert got.json()["value"] == body["value"]


async def test_recompute_is_reproducible(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)
    first = (await client.post(f"/api/v1/candidates/{cid}/score", headers=_auth(token))).json()
    second = (await client.post(f"/api/v1/candidates/{cid}/score", headers=_auth(token))).json()
    assert first["value"] == second["value"]
    assert first["breakdown"] == second["breakdown"]


async def test_score_without_consent_is_409(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    owner = await db_session.scalar(select(User).where(User.email == "admin@acme.com"))

    # Insert a candidate + document directly, WITHOUT any consent row.
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
            parsed={"skills": ["python", "fastapi"], "language": "en"},
        )
    )
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/candidates/{candidate.id}/score", headers=_auth(token)
    )
    assert resp.status_code == 409


async def test_score_cross_org_is_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    vid = await _vacancy(client, token_a)
    cid = await _upload(client, token_a, vid)
    resp = await client.post(f"/api/v1/candidates/{cid}/score", headers=_auth(token_b))
    assert resp.status_code == 404


async def test_unauthenticated_rejected(client):
    resp = await client.post(f"/api/v1/candidates/{uuid.uuid4()}/score")
    assert resp.status_code == 401


async def test_audit_score_computed_recorded(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)
    await client.post(f"/api/v1/candidates/{cid}/score", headers=_auth(token))
    events = (await db_session.scalars(select(AuditLog.event))).all()
    assert AuditEvent.score_computed in events


async def test_llm_provider_does_not_change_score(client, db_session, monkeypatch):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _vacancy(client, token)
    cid = await _upload(client, token, vid)

    baseline = (await client.post(f"/api/v1/candidates/{cid}/score", headers=_auth(token))).json()

    class _DifferentLLM:
        name = "stub"

        async def complete(self, prompt, *, system=None, **opts):
            return LLMResult(text="A COMPLETELY DIFFERENT EXPLANATION", model="stub-9")

    # Swap the LLM provider used by the scoring service to one returning different prose.
    monkeypatch.setattr(scoring_service, "get_llm_provider", lambda: _DifferentLLM())

    altered = (await client.post(f"/api/v1/candidates/{cid}/score", headers=_auth(token))).json()
    assert altered["value"] == baseline["value"]
    assert altered["breakdown"] == baseline["breakdown"]
    assert altered["narrative"]["rationale"] == "A COMPLETELY DIFFERENT EXPLANATION"
