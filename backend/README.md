# TalentTrust AI — Backend

Recruiter copilot that turns a CV + a structured vacancy into a verifiable, explainable
candidate dossier. See the feature docs under `../specs/001-talenttrust-mvp/`.

## Status

Phase 1 (Setup) + Phase 2 (Foundational) implemented: app skeleton, config, async DB layer,
provider abstraction (mock default), JWT auth + refresh, RBAC (`org_admin` / `recruiter` /
`viewer`), multi-tenant isolation, immutable audit log, Alembic migrations, and a deterministic
offline test suite. Vacancies, CV parsing, scoring, dossier, decisions, PDF export and the
frontend are implemented in later phases (see `tasks.md`).

## Run locally

```bash
cp .env.example .env          # adjust secrets; defaults use mock providers
# full stack (from repo root):
docker compose up --build     # postgres+pgvector, redis, backend
```

The backend runs `alembic upgrade head` on startup. API docs at http://localhost:8000/docs.

## Tests (deterministic, offline)

```bash
pip install ".[dev]"
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock pytest -q
ruff check app tests
mypy app
```

No real LLM/embedding calls are made in tests or CI (Constitution Principle III).

## Auth quickstart

```bash
# self-serve: create an org + its org_admin
curl -s localhost:8000/api/v1/auth/register \
  -H 'content-type: application/json' \
  -d '{"organization_name":"Acme","email":"admin@acme.com","password":"supersecret1"}'
# → { access_token, refresh_token }
```
