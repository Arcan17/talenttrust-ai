"""T027 — Vacancy CRUD: validation, RBAC, and multi-tenant isolation (US1)."""
from __future__ import annotations

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.user import Role, User

VALID_VACANCY = {
    "title": "Python Backend Developer",
    "description": "Build and maintain APIs.",
    "required_skills": ["python", "fastapi"],
    "desired_skills": ["docker"],
    "modality": "remote",
    "country": "CL",
    "salary_min": 1500,
    "salary_max": 2500,
    "seniority": "mid",
}


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org, email, password="supersecret1"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": password},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _add_user(db_session, *, owner_email: str, email: str, role: Role) -> User:
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
    return user


async def _token_for(db_session, *, owner_email: str, email: str, role: Role) -> str:
    user = await _add_user(db_session, owner_email=owner_email, email=email, role=role)
    return create_access_token(user.id, user.organization_id, user.role.value)


# --- creation & validation ---

async def test_admin_can_create_vacancy(client):
    token = await _register(client, "Acme", "admin@acme.com")
    resp = await client.post("/api/v1/vacancies", json=VALID_VACANCY, headers=_auth(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Python Backend Developer"
    assert body["required_skills"] == ["python", "fastapi"]
    assert body["status"] == "open"


async def test_recruiter_can_create_vacancy(client, db_session):
    await _register(client, "Acme", "admin@acme.com")
    token = await _token_for(
        db_session, owner_email="admin@acme.com", email="rec@acme.com", role=Role.recruiter
    )
    resp = await client.post("/api/v1/vacancies", json=VALID_VACANCY, headers=_auth(token))
    assert resp.status_code == 201


async def test_viewer_cannot_create_vacancy(client, db_session):
    await _register(client, "Acme", "admin@acme.com")
    token = await _token_for(
        db_session, owner_email="admin@acme.com", email="viewer@acme.com", role=Role.viewer
    )
    resp = await client.post("/api/v1/vacancies", json=VALID_VACANCY, headers=_auth(token))
    assert resp.status_code == 403


async def test_missing_title_is_422(client):
    token = await _register(client, "Acme", "admin@acme.com")
    payload = {k: v for k, v in VALID_VACANCY.items() if k != "title"}
    resp = await client.post("/api/v1/vacancies", json=payload, headers=_auth(token))
    assert resp.status_code == 422


async def test_empty_required_skills_is_422(client):
    token = await _register(client, "Acme", "admin@acme.com")
    payload = {**VALID_VACANCY, "required_skills": []}
    resp = await client.post("/api/v1/vacancies", json=payload, headers=_auth(token))
    assert resp.status_code == 422


async def test_blank_only_required_skills_is_422(client):
    token = await _register(client, "Acme", "admin@acme.com")
    payload = {**VALID_VACANCY, "required_skills": ["   ", ""]}
    resp = await client.post("/api/v1/vacancies", json=payload, headers=_auth(token))
    assert resp.status_code == 422


async def test_invalid_modality_is_422(client):
    token = await _register(client, "Acme", "admin@acme.com")
    payload = {**VALID_VACANCY, "modality": "hybridd"}
    resp = await client.post("/api/v1/vacancies", json=payload, headers=_auth(token))
    assert resp.status_code == 422


# --- listing, retrieval, isolation ---

async def test_list_returns_only_own_org_vacancies(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")

    await client.post("/api/v1/vacancies", json=VALID_VACANCY, headers=_auth(token_a))

    list_a = await client.get("/api/v1/vacancies", headers=_auth(token_a))
    assert list_a.status_code == 200
    assert len(list_a.json()) == 1

    list_b = await client.get("/api/v1/vacancies", headers=_auth(token_b))
    assert list_b.status_code == 200
    assert list_b.json() == []


async def test_get_own_vacancy_ok(client):
    token = await _register(client, "Acme", "admin@acme.com")
    created = await client.post(
        "/api/v1/vacancies", json=VALID_VACANCY, headers=_auth(token)
    )
    vid = created.json()["id"]
    resp = await client.get(f"/api/v1/vacancies/{vid}", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == vid


async def test_get_cross_org_vacancy_is_404(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")
    created = await client.post(
        "/api/v1/vacancies", json=VALID_VACANCY, headers=_auth(token_a)
    )
    vid = created.json()["id"]
    resp = await client.get(f"/api/v1/vacancies/{vid}", headers=_auth(token_b))
    assert resp.status_code == 404


async def test_unauthenticated_rejected(client):
    assert (await client.get("/api/v1/vacancies")).status_code == 401
    assert (
        await client.post("/api/v1/vacancies", json=VALID_VACANCY)
    ).status_code == 401
