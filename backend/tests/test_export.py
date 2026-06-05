"""Phase 6 — dossier PDF export: content, content-type, decision inclusion, audit, RBAC."""
from __future__ import annotations

import uuid

import pymupdf
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


def _pdf_text(data: bytes) -> str:
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        raw = "\n".join(doc.load_page(i).get_text("text") for i in range(doc.page_count))
    finally:
        doc.close()
    # Normalize whitespace so phrases split across line wraps still match.
    return " ".join(raw.lower().split())


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


async def _candidate(client, token, *, with_dossier=True, display_name="Jane Doe"):
    vid = await _vacancy(client, token)
    files = {"file": ("cv.pdf", make_pdf(STRONG_CV), PDF_MIME)}
    up = await client.post(
        f"/api/v1/vacancies/{vid}/candidates",
        files=files,
        data={**CONSENT, "display_name": display_name},
        headers=_auth(token),
    )
    cid = up.json()["id"]
    if with_dossier:
        r = await client.post(f"/api/v1/candidates/{cid}/dossier", headers=_auth(token))
        assert r.status_code == 201
    return cid


async def test_export_success_pdf(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _candidate(client, token)
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier/export", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert f"talenttrust-dossier-{cid}.pdf" in resp.headers.get("content-disposition", "")
    assert resp.content[:4] == b"%PDF"


async def test_pdf_contains_main_sections(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _candidate(client, token, display_name="Jane Doe")
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier/export", headers=_auth(token))
    text = _pdf_text(resp.content).lower()
    for section in ("resumen", "score", "brechas", "inconsistencias", "preguntas de entrevista"):
        assert section in text, f"missing section: {section}"
    assert "jane doe" in text  # candidate name
    assert "python backend developer" in text  # vacancy
    assert "no constituye una decisión automática" in text  # legal note


async def test_pdf_includes_human_decision_when_present(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _candidate(client, token)
    await client.post(
        f"/api/v1/candidates/{cid}/decision",
        json={"human_outcome": "interview", "note": "Great fit"},
        headers=_auth(token),
    )
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier/export", headers=_auth(token))
    text = _pdf_text(resp.content).lower()
    assert "decisión humana registrada" in text
    assert "interview" in text
    assert "great fit" in text


async def test_audit_pdf_exported(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _candidate(client, token)
    await client.post(f"/api/v1/candidates/{cid}/dossier/export", headers=_auth(token))
    events = (await db_session.scalars(select(AuditLog.event))).all()
    assert AuditEvent.pdf_exported in events


async def test_export_without_dossier_409(client):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _candidate(client, token, with_dossier=False)
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier/export", headers=_auth(token))
    assert resp.status_code == 409


async def test_export_cross_org_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    cid = await _candidate(client, token_a)
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier/export", headers=_auth(token_b))
    assert resp.status_code == 404


async def test_export_unauthenticated_401(client):
    resp = await client.post(f"/api/v1/candidates/{uuid.uuid4()}/dossier/export")
    assert resp.status_code == 401


async def test_viewer_cannot_export(client, db_session):
    token = await _register(client, "Acme", "admin@acme.com")
    cid = await _candidate(client, token)
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
    resp = await client.post(f"/api/v1/candidates/{cid}/dossier/export", headers=_auth(vtoken))
    assert resp.status_code == 403
