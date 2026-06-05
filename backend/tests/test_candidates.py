"""Phase 4a — candidate upload + consent endpoint: RBAC, validation, isolation, audit."""
from __future__ import annotations

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.audit_log import AuditEvent, AuditLog
from app.models.consent import Consent
from app.models.user import Role, User
from tests.cv_fixtures import ENGLISH_CV, make_empty_pdf, make_pdf

VACANCY = {
    "title": "Python Backend Developer",
    "description": "APIs",
    "required_skills": ["python", "fastapi"],
    "desired_skills": ["docker"],
    "modality": "remote",
    "country": "CL",
    "seniority": "mid",
}
PDF_MIME = "application/pdf"
CONSENT = {"consent_version": "v1", "consent_scope": "professional-evaluation"}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org, email, password="supersecret1"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": password},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _create_vacancy(client, token):
    resp = await client.post("/api/v1/vacancies", json=VACANCY, headers=_auth(token))
    assert resp.status_code == 201
    return resp.json()["id"]


async def _viewer_token(db_session, owner_email):
    owner = await db_session.scalar(select(User).where(User.email == owner_email))
    viewer = User(
        organization_id=owner.organization_id,
        email="viewer@acme.com",
        hashed_password=hash_password("supersecret1"),
        role=Role.viewer,
    )
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    return create_access_token(viewer.id, viewer.organization_id, viewer.role.value)


async def _upload(
    client, token, vid, *, data=None, filename="cv.pdf", ctype=PDF_MIME, consent=CONSENT
):
    payload = data if data is not None else make_pdf(ENGLISH_CV)
    files = {"file": (filename, payload, ctype)}
    return await client.post(
        f"/api/v1/vacancies/{vid}/candidates", files=files, data=consent, headers=_auth(token)
    )


async def test_recruiter_uploads_valid_cv(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    resp = await _upload(client, token, vid)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "received"
    assert body["vacancy_id"] == vid
    assert body["document"]["content_type"] == "pdf"
    assert body["document"]["parsed"]["language"] == "en"
    assert body["consent"]["version"] == "v1"


async def test_viewer_cannot_upload(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    vtoken = await _viewer_token(db_session, "admin@acme.com")
    resp = await _upload(client, vtoken, vid)
    assert resp.status_code == 403


async def test_upload_without_consent_is_422(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    resp = await _upload(client, token, vid, consent={})
    assert resp.status_code == 422


async def test_reject_invalid_type(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    resp = await _upload(client, token, vid, data=b"hello", filename="cv.txt", ctype="text/plain")
    assert resp.status_code == 400


async def test_reject_oversize(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    big = b"%PDF-1.4\n" + b"0" * (5 * 1024 * 1024 + 10)
    resp = await _upload(client, token, vid, data=big, filename="big.pdf")
    assert resp.status_code == 413


async def test_reject_no_text_pdf(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    resp = await _upload(client, token, vid, data=make_empty_pdf(), filename="scan.pdf")
    assert resp.status_code == 400


async def test_get_candidate_own_ok(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    cid = (await _upload(client, token, vid)).json()["id"]
    resp = await client.get(f"/api/v1/candidates/{cid}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == cid
    assert resp.json()["document"]["parsed"]["skills"]


async def test_get_candidate_cross_org_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    vid = await _create_vacancy(client, token_a)
    cid = (await _upload(client, token_a, vid)).json()["id"]
    resp = await client.get(f"/api/v1/candidates/{cid}", headers=_auth(token_b))
    assert resp.status_code == 404


async def test_upload_to_cross_org_vacancy_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    vid_a = await _create_vacancy(client, token_a)
    resp = await _upload(client, token_b, vid_a)
    assert resp.status_code == 404


async def test_unauthenticated_rejected(client):
    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    files = {"file": ("cv.pdf", make_pdf(ENGLISH_CV), PDF_MIME)}
    resp = await client.post(
        f"/api/v1/vacancies/{vid}/candidates", files=files, data=CONSENT
    )
    assert resp.status_code == 401


async def test_consent_and_audit_recorded(client, db_session):
    import uuid

    token = await _register(client, "Acme", "admin@acme.com")
    vid = await _create_vacancy(client, token)
    cid = uuid.UUID((await _upload(client, token, vid)).json()["id"])

    consents = (
        await db_session.scalars(select(Consent).where(Consent.candidate_id == cid))
    ).all()
    assert len(consents) == 1 and consents[0].version == "v1"

    events = (await db_session.scalars(select(AuditLog.event))).all()
    assert AuditEvent.cv_parsed in events
