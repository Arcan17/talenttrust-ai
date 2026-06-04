"""T020 — auth: register, login, refresh, and write protection."""
from __future__ import annotations


async def _register(client, org="Acme", email="admin@acme.com", password="supersecret1"):
    return await client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": password},
    )


async def test_register_returns_tokens(client):
    resp = await _register(client)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


async def test_register_duplicate_org_conflicts(client):
    await _register(client)
    resp = await _register(client, email="other@acme.com")
    assert resp.status_code == 409


async def test_login_success_and_failure(client):
    await _register(client, email="admin@acme.com", password="supersecret1")

    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "supersecret1"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


async def test_refresh_returns_new_access_token(client):
    reg = await _register(client)
    refresh_token = reg.json()["refresh_token"]
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_me_requires_token(client):
    # No Authorization header → 401
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401

    reg = await _register(client)
    token = reg.json()["access_token"]
    ok = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert ok.status_code == 200
    assert ok.json()["role"] == "org_admin"


async def test_audit_login_events_written(client, db_session):
    from sqlalchemy import select

    from app.models.audit_log import AuditEvent, AuditLog

    await _register(client, email="admin@acme.com", password="supersecret1")
    await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "wrong"},
    )
    events = (await db_session.scalars(select(AuditLog.event))).all()
    assert AuditEvent.login_success in events
    assert AuditEvent.login_failed in events
