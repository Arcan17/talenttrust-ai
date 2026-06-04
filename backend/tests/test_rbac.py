"""T021 — RBAC + multi-tenant isolation on the org-scoped /users endpoint."""
from __future__ import annotations

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.models.user import Role, User


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client, org, email, password="supersecret1"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": password},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]


async def _add_user(db_session, *, org_email_owner: str, email: str, role: Role) -> User:
    owner = await db_session.scalar(select(User).where(User.email == org_email_owner))
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


async def test_admin_can_list_users(client):
    token = await _register(client, "Acme", "admin@acme.com")
    resp = await client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 200
    emails = [u["email"] for u in resp.json()]
    assert "admin@acme.com" in emails


async def test_viewer_forbidden_on_admin_endpoint(client, db_session):
    await _register(client, "Acme", "admin@acme.com")
    viewer = await _add_user(
        db_session, org_email_owner="admin@acme.com", email="viewer@acme.com", role=Role.viewer
    )
    token = create_access_token(viewer.id, viewer.organization_id, viewer.role.value)
    resp = await client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 403


async def test_recruiter_forbidden_on_admin_endpoint(client, db_session):
    await _register(client, "Acme", "admin@acme.com")
    rec = await _add_user(
        db_session, org_email_owner="admin@acme.com", email="rec@acme.com", role=Role.recruiter
    )
    token = create_access_token(rec.id, rec.organization_id, rec.role.value)
    resp = await client.get("/api/v1/users", headers=_auth(token))
    assert resp.status_code == 403


async def test_tenant_isolation_users_scoped_to_own_org(client):
    token_a = await _register(client, "Acme", "admin@acme.com")
    token_b = await _register(client, "Beta", "admin@beta.com")

    resp_a = await client.get("/api/v1/users", headers=_auth(token_a))
    emails_a = {u["email"] for u in resp_a.json()}
    assert emails_a == {"admin@acme.com"}
    assert "admin@beta.com" not in emails_a

    resp_b = await client.get("/api/v1/users", headers=_auth(token_b))
    emails_b = {u["email"] for u in resp_b.json()}
    assert emails_b == {"admin@beta.com"}


async def test_unauthenticated_rejected(client):
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401
