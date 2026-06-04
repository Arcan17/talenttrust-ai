# Implementation Plan: AI Candidate Dossier (TalentTrust AI — MVP Phase 1)

**Branch**: `001-talenttrust-mvp` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-talenttrust-mvp/spec.md`

## Summary

TalentTrust AI Phase 1 turns a candidate CV (PDF/DOCX, ≤5 MB, text-extractable) plus a structured
job vacancy into a verifiable, explainable candidate dossier: a deterministic 0–100 fit score with a
fixed-weight breakdown, an LLM-written explanation that never alters the number, detected skills with
evidence, gaps, neutral inconsistencies, suggested interview questions, a non-binding recommendation,
a human-recorded final decision, and a PDF export. The technical approach maximizes reuse of two
mature in-house MVPs: **AgentDesk AI** (multi-tenant auth/RBAC, immutable audit log, human-in-the-loop
pattern, provider abstraction, Celery/Redis, deterministic test harness) and **JobOps AI** (the
deterministic, reproducible, breakdown-persisting scoring engine). New modules cover CV parsing,
fairness exclusion, inconsistency detection, interview-question generation, and PDF export.

## Technical Context

**Language/Version**: Python 3.11+ (backend), TypeScript 5 / Node 20 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async, asyncpg), Pydantic v2, Alembic, Celery +
Redis, pgvector; PyMuPDF (PDF text extraction) + python-docx (DOCX) for CV parsing; a PDF writer
(WeasyPrint or ReportLab) for dossier export; Next.js 15 + Tailwind v4 + React 19 (frontend). LLM and
embedding access strictly behind `LLMProvider` / `EmbeddingProvider` interfaces (mock/anthropic/openai).

**Storage**: PostgreSQL 16 with the pgvector extension (single database); CV files stored as bytes/
object reference with a SHA-256 hash; SQLite in-memory (with a JSON-vector fallback) for tests.

**Testing**: pytest + pytest-asyncio, mock providers forced (`LLM_PROVIDER=mock`,
`EMBEDDING_PROVIDER=mock`), eager Celery execution in tests. Frontend: lightweight component checks.

**Target Platform**: Linux server (Docker Compose: postgres+pgvector, redis, backend, worker,
frontend).

**Project Type**: Web application (backend + frontend) with an async worker.

**Performance Goals**: CV→dossier generation under ~3 minutes per candidate end-to-end (SC-001); PDF
export under 30 s (SC-008). Single-candidate evaluation flow (no mass ranking in Phase 1).

**Constraints**: Score MUST be deterministic and reproducible (LLM never produces the number);
sensitive attributes MUST be excluded from scoring; every shown conclusion MUST cite a source; audit
log MUST be immutable; all data tenant-scoped; no real LLM calls in CI; no hardcoded secrets.

**Scale/Scope**: MVP scale — small recruiting teams (pyme/startup/consultora). One candidate evaluated
at a time against a vacancy. ~10 entities, ~4 user stories, ~29 functional requirements.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies |
|-----------|------------------------|
| I. Evidence-Based Scoring | Every dossier conclusion (skill, gap, inconsistency) carries an `evidence` reference; the dossier layer rejects unsourced claims. Score breakdown is persisted and shown. |
| II. Providers Behind Interfaces | All LLM/embedding use goes through `app/providers` (base/factory/mock/anthropic/openai copied from AgentDesk). CV parser uses the LLM only via the interface to structure already-extracted text. |
| III. Deterministic Tests, No Paid APIs in CI | Mock providers forced in `conftest.py`; required coverage: auth/RBAC, CV parsing, scoring (reconciliation + reproducibility), fairness exclusion, inconsistency detection, interview questions, decision HITL, audit, PDF. |
| IV. Deterministic Score, LLM Explains Only | `app/scoring/components.py` + `weights.py` compute the number deterministically; `scoring_service` calls the LLM only for the narrative, which never feeds back into the value. |
| V. Reproducible Scoring | No wall-clock/randomness in scoring; embeddings from the mock provider are deterministic; a test asserts identical score+breakdown for identical inputs. |
| VI. Security & Privacy by Design | JWT + RBAC per endpoint; Pydantic v2 validation; `.env.example`; consent captured/versioned before analysis; candidate hard-delete + configurable TTL; no PII/stack-trace leakage. |
| VII. Observability & Immutable Audit Log | `audit_service` (append-only) records `cv_parsed`, `dossier_generated`, `score_computed`, `decision_recorded`, `pdf_exported` (+ login events) with actor/org/target/timestamp/meta. |
| VIII. Multi-Tenant Isolation | Every entity carries `organization_id`; services filter by the authenticated user's org; roles `org_admin`/`recruiter`/`viewer`. |
| IX. Human-in-the-Loop, Human-Final-Decision | No automated final outcome; `Decision` is created only by a human action and records the AI recommendation shown + the human outcome. Recommendation is explicitly non-binding. |
| X. Fairness, Non-Discrimination & Consent by Design | `app/scoring/fairness_guard.py` strips sensitive attributes before any feature reaches scoring; neutral "requires review" language; no criminal-record search, no scraping, no fabricated conclusions; consent versioned. |

**Result**: PASS — no violations; no entries required in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-talenttrust-mvp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (openapi.md)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── core/                  # config, security (JWT+refresh), deps  [reuse: AgentDesk]
│   ├── rbac.py                # require_role(org_admin/recruiter/viewer)  [reuse: AgentDesk]
│   ├── db/                    # engine, session, base mixins, types.py (Embedding)  [reuse: AgentDesk]
│   ├── providers/             # base/factory/mock/anthropic/openai  [reuse: AgentDesk+JobOps]
│   ├── models/                # organization, user, vacancy, candidate, candidate_document,
│   │                          # consent, dossier, score, decision, audit_log
│   ├── schemas/               # Pydantic v2 request/response models
│   ├── services/              # vacancy_service, candidate_service, cv_parser, dossier_service,
│   │                          # scoring_service [reuse: JobOps], inconsistency_detector,
│   │                          # interview_questions, decision_service [HITL pattern: AgentDesk],
│   │                          # report_pdf, audit_service [reuse: AgentDesk], retention_service
│   ├── scoring/               # weights.py, components.py [reuse+invert: JobOps], fairness_guard.py (new)
│   ├── workers/               # celery_app, tasks (CV analysis async; eager in tests)  [reuse: AgentDesk]
│   ├── api/v1/                # auth, vacancies, candidates, dossiers, decisions, exports, health
│   └── main.py                # app factory (CORS, rate limit, logging, routers)
├── alembic/                   # migrations (enable pgvector → org/user → domain tables)
└── tests/                     # conftest.py [reuse: AgentDesk] + per-module deterministic tests

frontend/
├── app/                       # Next.js 15 App Router: login, (dashboard) vacancies, candidates, dossier
├── components/                # ScoreCard, Breakdown, EvidenceList, DossierView, DecisionPanel  [adapt: JobOps]
└── lib/                       # api client, types, auth

docker-compose.yml             # postgres+pgvector, redis, backend, worker, frontend
.github/workflows/ci.yml       # ruff → mypy → alembic upgrade → pytest (mock providers)
```

**Structure Decision**: Web application (Option 2) — a FastAPI backend with an async Celery worker and
a Next.js frontend, mirroring the proven AgentDesk/JobOps layout so reused modules drop in with minimal
adaptation.

## Reuse Map (avoid reinventing)

| Need | Source to copy/adapt | Adaptation |
|------|----------------------|------------|
| Auth, JWT+refresh, deps, RBAC | `agentdesk-ai/backend/app/core/*`, `app/rbac.py` | Rename roles to `org_admin`/`recruiter`/`viewer` |
| DB infra (async engine, mixins, Embedding type) | `agentdesk-ai/backend/app/db/*` | As-is |
| Provider abstraction | `agentdesk-ai/backend/app/providers/*` | As-is |
| Immutable audit log | `agentdesk-ai/backend/app/models/audit_log.py`, `app/services/audit_service.py` | Extend `AuditEvent` enum with the 5 dossier events |
| HITL approve/reject + transitions | `agentdesk-ai/backend/app/services/ticket_service.py` | Adapt to `decision_service` (interview/review/discard) |
| Async jobs + eager test flag | `agentdesk-ai/backend/app/workers/*` | Task = CV analysis pipeline |
| Test harness | `agentdesk-ai/backend/tests/conftest.py` | As-is |
| Deterministic scoring engine | `jobops-ai/backend/app/scoring/weights.py`, `components.py` | Invert to candidate↔vacancy; 6 factors per FR-013 |
| Score breakdown + LLM narrative | `jobops-ai/backend/app/services/scoring_service.py`, `app/models/score.py` | 0–100 scale; narrative never alters number |
| Scoring tests | `jobops-ai/backend/tests/test_scoring.py` | Reuse reconciliation + reproducibility assertions |

## New Modules (Phase 1 build)

- `app/services/cv_parser.py` — PyMuPDF (PDF) + python-docx (DOCX) → raw text; reject non-PDF/DOCX,
  >5 MB, and image-only/no-text files; LLM (via provider interface) structures text into a Pydantic
  `ParsedCV`. Emits `cv_parsed`.
- `app/scoring/fairness_guard.py` — pure function that strips/blocks sensitive attributes (age,
  gender, nationality, marital status, health, religion, political affiliation, exact address) from
  any feature reaching the scoring engine; unit-tested that altering a sensitive field doesn't change
  the score (SC-006).
- `app/services/inconsistency_detector.py` — deterministic checks for the 7 signals in FR-019, output
  in neutral "requires review" language with evidence references.
- `app/services/interview_questions.py` — LLM node over the dossier + gaps producing suggested
  questions (explanatory only; not part of the score).
- `app/services/report_pdf.py` — renders the dossier (summary, score+breakdown, evidence, gaps,
  inconsistencies, questions, recorded decision) to PDF. Emits `pdf_exported`.
- `app/services/retention_service.py` — hard-delete of a candidate's data on demand; configurable TTL
  via env (default 180 days); no mandatory auto-purge in Phase 1.

## Implementation Phases (high level; detailed tasks via /speckit-tasks)

1. **Skeleton** — backend app factory, config, DB engine, Docker Compose, CI, copied `providers` +
   `conftest`. Health endpoint green.
2. **Auth & Multi-tenant** — Organization, User, JWT+refresh, RBAC roles, login audit events.
3. **Vacancies** — Vacancy model/schema/service/API; org-scoped CRUD; validation (FR-004..006).
4. **CV Parser & Consent** — CandidateDocument, Consent (versioned), `cv_parser` with rejection rules;
   `cv_parsed` audit; consent-gate before analysis (FR-007..010, FR-008/009).
5. **Scoring & Dossier** — port JobOps scoring inverted to 6 factors; `fairness_guard`;
   `inconsistency_detector`; `interview_questions`; assemble `Dossier` + `Score` with evidence;
   `score_computed`/`dossier_generated` audit. Reproducibility + reconciliation tests (FR-011..021).
6. **Decision & Audit** — `decision_service` (HITL, human-final), `Decision` model, `decision_recorded`
   audit; assert no automatic final outcome (FR-022..024, FR-026).
7. **PDF Export** — `report_pdf`, export endpoint, `pdf_exported` audit (FR-025).
8. **Retention** — hard-delete endpoint + configurable TTL (FR-027).
9. **Frontend** — recruiter dashboard: vacancy list/create, CV upload + consent, dossier view
   (score + breakdown + evidence + inconsistencies + questions), decision panel, PDF export.

Each phase closes with a change summary, file list, how-to-test, and a passing test run for affected
modules (per constitution Development Workflow). A phase MUST NOT advance while critical errors remain.

## Complexity Tracking

No constitution violations — section intentionally empty.
