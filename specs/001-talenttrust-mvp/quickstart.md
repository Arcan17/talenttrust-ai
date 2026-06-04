# Quickstart: TalentTrust AI — AI Candidate Dossier (MVP Phase 1)

This is the developer walkthrough for running and validating the feature locally. The stack mirrors
AgentDesk/JobOps, so the workflow will be familiar.

## Prerequisites

- Docker + Docker Compose
- Python 3.11+ and Node 20+ (for running tests/frontend outside Docker, optional)

## Run the full stack

```bash
cp backend/.env.example backend/.env   # fill secrets; defaults use mock providers
docker compose up --build              # postgres+pgvector, redis, backend, worker, frontend
```

- Backend API: http://localhost:8000 (OpenAPI docs at `/docs`)
- Frontend: http://localhost:3000
- Migrations (`alembic upgrade head`) run on backend startup; a seed org + recruiter user is created
  from `SEED_*` env vars.

## Default providers

`LLM_PROVIDER=mock` and `EMBEDDING_PROVIDER=mock` by default — the app runs fully offline and
deterministically. Set `LLM_PROVIDER=anthropic|openai` with the matching API key to use a real model
(narrative text only; the score is unaffected).

## End-to-end happy path

1. **Login**: `POST /api/v1/auth/login` with the seeded recruiter credentials → copy `access_token`.
2. **Create a vacancy**: `POST /api/v1/vacancies` with title, `required_skills`, modality, country,
   seniority.
3. **Upload a CV + consent**: `POST /api/v1/vacancies/{vacancy_id}/candidates` (multipart: a small
   text-based PDF/DOCX ≤5 MB + `consent {version, scope}`). → candidate `received`.
4. **Generate the dossier**: `POST /api/v1/candidates/{id}/dossier` → score (0–100) + breakdown,
   skills with evidence, gaps, neutral inconsistencies, interview questions, non-binding recommendation.
5. **Record the human decision**: `POST /api/v1/candidates/{id}/decision` with
   `human_outcome=interview|review|discard`.
6. **Export PDF**: `POST /api/v1/candidates/{id}/dossier/export` → downloadable PDF.
7. **Inspect audit**: `GET /api/v1/audit` (as org_admin) → entries for `cv_parsed`, `score_computed`,
   `dossier_generated`, `decision_recorded`, `pdf_exported`.

Or do all of the above from the frontend recruiter dashboard at http://localhost:3000.

## Run tests (deterministic, offline)

```bash
cd backend
LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock pytest -q
```

Key assertions to expect green:

- **Reproducibility**: same CV + vacancy → identical `score.value` and `breakdown`.
- **Reconciliation**: weighted breakdown components sum to `score.value` within rounding.
- **Fairness**: mutating only a sensitive attribute (e.g. age) leaves the score unchanged.
- **Consent gate**: dossier generation without consent → `409`.
- **CV rejection**: non-PDF/DOCX, >5 MB, and no-text files are rejected with no dossier created.
- **Tenant isolation**: cross-org access → `404`; `viewer` write → `403`.
- **Human-final**: no `Decision`/final outcome is ever created without an explicit human request.
- **Audit**: each consequential action writes an immutable audit entry.

## CI

GitHub Actions runs `ruff` → `mypy` → `alembic upgrade head` → `pytest` with mock providers only (no
paid API calls), matching the constitution's deterministic-CI requirement.
