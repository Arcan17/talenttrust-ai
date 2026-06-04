"""T011 — skeleton smoke test."""
from __future__ import annotations


async def test_health_ok(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


async def test_root_ok(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "TalentTrust AI"
