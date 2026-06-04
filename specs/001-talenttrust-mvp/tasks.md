# Tasks: AI Candidate Dossier (TalentTrust AI — MVP Phase 1)

**Feature**: `001-talenttrust-mvp` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

**Inputs**: plan.md, data-model.md, contracts/openapi.md, research.md, quickstart.md

## Conventions

- Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`
- `[P]` = parallelizable (different files, no dependency on an incomplete task).
- **Reuse tags**: `[reuse:agentdesk]` / `[reuse:jobops]` = copy & adapt from that sibling repo
  (`/Users/bastian/Documents/agentdesk-ai/backend/`, `/Users/bastian/Documents/jobops-ai/backend/`).
  `[new]` = module built fresh for TalentTrust.
- Tests are deterministic with mock providers forced (`LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=mock`),
  per constitution Principle III.

---

## Phase 1: Setup (project skeleton)

- [X] T001 Create backend project structure (`backend/app/{core,db,providers,models,schemas,services,scoring,workers,api/v1}`, `backend/tests/`, `backend/alembic/`) per plan.md
- [X] T002 Add `backend/pyproject.toml` with deps (FastAPI, SQLAlchemy 2.0, asyncpg, pydantic v2, alembic, celery, redis, pgvector, pymupdf, python-docx, weasyprint, python-jose, bcrypt, structlog) + ruff/mypy/pytest config
- [X] T003 [P] Add `backend/.env.example` documenting every variable (DB, Redis, JWT, provider keys, `LLM_PROVIDER=mock`, `EMBEDDING_PROVIDER=mock`, `CANDIDATE_DATA_TTL_DAYS=180`, `MAX_CV_SIZE_BYTES=5242880`, SEED_*)
- [X] T004 [P] Add `docker-compose.yml` (postgres+pgvector, redis, backend, worker, frontend)
- [X] T005 [P] Add `.github/workflows/ci.yml` (ruff → mypy → alembic upgrade → pytest with mock providers)
- [X] T006 [P] [reuse:agentdesk] Copy `app/core/{config.py,logging.py}` and adapt settings to TalentTrust env vars
- [X] T007 [reuse:agentdesk] Copy `app/db/{engine.py,session.py,base.py,types.py}` (async engine, UUID/Timestamp mixins, portable Embedding type)
- [X] T008 [P] [reuse:agentdesk] Copy `app/providers/{base.py,factory.py,mock.py,anthropic.py,openai.py}` (LLM/embedding interfaces, mock default)
- [X] T009 [reuse:agentdesk] Copy `backend/tests/conftest.py` (mock providers + in-memory SQLite + eager Celery fixtures)
- [X] T010 Create `app/main.py` app factory (CORS, rate limit, structured logging, exception handlers, router include) + `GET /health`
- [X] T011 Test: `tests/test_health.py` asserts `GET /health` → 200 (smoke; confirms skeleton boots)

**Checkpoint**: backend boots, health green, `pytest` runs offline.

---

## Phase 2: Foundational — Auth, Multi-tenant, Audit (BLOCKS all user stories)

- [X] T012 [reuse:agentdesk] Copy/adapt `app/core/security.py` (JWT access+refresh, bcrypt hash/verify)
- [X] T013 [P] [reuse:agentdesk] Create `app/models/organization.py` (Organization) and `app/models/user.py` (User with role enum `org_admin|recruiter|viewer`, `uq_user_org_email`)
- [X] T014 [reuse:agentdesk] Copy/adapt `app/core/deps.py` (`get_db`, `get_current_user`) and `app/rbac.py` (`require_role`)
- [X] T015 [P] [reuse:agentdesk] Create `app/models/audit_log.py` (immutable AuditLogEntry) with `AuditEvent` enum incl. `cv_parsed, dossier_generated, score_computed, decision_recorded, pdf_exported, login_success, login_failed`
- [X] T016 [P] [reuse:agentdesk] Copy/adapt `app/services/audit_service.py` (append-only `record(...)`)
- [X] T017 [reuse:agentdesk] Create `app/api/v1/auth.py` (`POST /auth/login`, `POST /auth/refresh`) emitting login audit events + `app/schemas/auth.py`
- [X] T018 Create `app/seed.py` (seed Organization + recruiter user from env) wired into startup
- [X] T019 Alembic migration `0001_enable_pgvector` (CREATE EXTENSION vector) and `0002_org_user_audit` (organizations, users, audit_log)
- [X] T020 [P] Test: `tests/test_auth.py` (login success/failure, refresh, write rejected without token)
- [X] T021 [P] Test: `tests/test_rbac.py` (viewer gets 403 on writes; cross-org access returns 404)

**Checkpoint**: auth works, RBAC + org-scoping enforced, audit log writable. User stories can start.

---

## Phase 3: User Story 1 — Recruiter creates a structured vacancy (Priority: P1)

**Goal**: A recruiter creates/lists/views org-scoped vacancies with validated required fields.
**Independent test**: Create a vacancy with all fields → persisted & listed within the org; missing
required field → 422; another org cannot see it.

- [ ] T022 [P] [US1] Create `app/models/vacancy.py` (Vacancy: title, description, required_skills, desired_skills, modality, country, salary_min/max, seniority, requirements_embedding) per data-model.md
- [ ] T023 [P] [US1] Create `app/schemas/vacancy.py` (VacancyCreate/VacancyOut, Pydantic v2 validation: title + ≥1 required_skill)
- [ ] T024 [US1] Create `app/services/vacancy_service.py` (create/list/get, org-scoped; compute `requirements_embedding` via embedding provider)
- [ ] T025 [US1] Create `app/api/v1/vacancies.py` (`POST /vacancies` [org_admin,recruiter], `GET /vacancies`, `GET /vacancies/{id}`)
- [ ] T026 [US1] Alembic migration `0003_vacancies`
- [ ] T027 [P] [US1] Test: `tests/test_vacancies.py` (create happy path, 422 on missing required fields, list scoping, cross-org 404)

**Checkpoint**: US1 independently demoable — vacancy CRUD with validation and isolation.

---

## Phase 4: User Story 2 — Upload CV + consent → explainable dossier (Priority: P1)

**Goal**: Recruiter uploads a CV (PDF/DOCX ≤5 MB) with consent; system parses it, computes a
deterministic 0–100 score with breakdown, and assembles an evidence-based dossier.
**Independent test**: Upload a text PDF against a vacancy with consent → dossier with score+breakdown
(reconciling), skills+evidence, gaps, neutral inconsistencies, interview questions; repeating yields
identical score; no consent → 409; sensitive attribute change doesn't move the score.

### Models & schemas

- [ ] T028 [P] [US2] Create `app/models/candidate.py` (Candidate: vacancy_id, display_name, status `received|analyzed`)
- [ ] T029 [P] [US2] Create `app/models/candidate_document.py` (CandidateDocument: filename, content_type, size_bytes, sha256, raw_text, parsed JSON)
- [ ] T030 [P] [US2] Create `app/models/consent.py` (Consent: version, scope, granted_at, granted_by_user_id; append-only)
- [ ] T031 [P] [US2] Create `app/models/dossier.py` (Dossier: summary, skills[{name,evidence[]}], gaps, inconsistencies, interview_questions, recommendation) and `app/models/score.py` (value 0–100, breakdown JSON, narrative JSON) [reuse:jobops score shape]
- [ ] T032 [P] [US2] Create `app/schemas/{candidate,dossier,score}.py` (Pydantic v2; ParsedCV schema for structured CV)

### CV parsing (new)

- [ ] T033 [US2] [new] Create `app/services/cv_parser.py`: validate type (pdf/docx) + size (≤5 MB); extract text with PyMuPDF/python-docx; reject empty/no-text; LLM (provider interface) structures text → `ParsedCV`. Emit `cv_parsed`
- [ ] T034 [P] [US2] Test: `tests/test_cv_parser.py` (reject non-pdf/docx, >5 MB, no-text/image-only; happy path returns ParsedCV deterministically under mock; **explicit ES and EN CV cases both parse** — FR-029)

### Scoring engine (reuse + invert) + fairness

- [ ] T035 [US2] [reuse:jobops] Create `app/scoring/weights.py` with the 6 fixed factors (skills 35, experience 20, seniority 15, modality_location 10, evidence 10, inconsistency_penalty 10)
- [ ] T036 [US2] [reuse:jobops] Create `app/scoring/components.py` (deterministic sub-scores; embeddings for skills/experience/evidence, rules for seniority/modality) inverted to candidate↔vacancy, 0–100 scale
- [ ] T037 [US2] [new] Create `app/scoring/fairness_guard.py` (strip sensitive attributes before scoring)
- [ ] T038 [US2] [reuse:jobops] Create `app/services/scoring_service.py` (compute components → 0–100 value + persisted breakdown; LLM narrative that never alters the number). Emit `score_computed`
- [ ] T039 [P] [US2] Test: `tests/test_scoring.py` — weights sum to 100; breakdown reconciles to value; **same input → identical score** (reproducibility); strong vs weak ordering
- [ ] T040 [P] [US2] Test: `tests/test_fairness.py` — mutating only a sensitive attribute (age/marital status) leaves the score unchanged (SC-006)

### Inconsistencies, interview questions, dossier assembly (new)

- [ ] T041 [P] [US2] [new] Create `app/services/inconsistency_detector.py` (7 signals from FR-019; neutral "requires review"; evidence refs)
- [ ] T042 [P] [US2] [new] Create `app/services/interview_questions.py` (LLM over dossier+gaps; explanatory only)
- [ ] T043 [US2] Create `app/services/dossier_service.py` orchestrating parse → fairness → score → inconsistencies → questions → assemble Dossier; enforce evidence-on-every-conclusion; consent gate (409 if none). Emit `dossier_generated`
- [ ] T044 [US2] [reuse:agentdesk] Create `app/workers/{celery_app.py,tasks.py}` running the CV-analysis pipeline async with eager flag for tests
- [ ] T045 [US2] Create `app/api/v1/candidates.py` (`POST /vacancies/{id}/candidates` multipart upload+consent → 202; `GET /candidates/{id}`) and `app/api/v1/dossiers.py` (`POST /candidates/{id}/dossier`, `GET /candidates/{id}/dossier`)
- [ ] T046 [US2] Alembic migration `0004_candidates_dossier` (candidates, candidate_documents, consents, dossiers, scores)
- [ ] T047 [P] [US2] Test: `tests/test_consent_gate.py` (dossier without consent → 409)
- [ ] T048 [P] [US2] Test: `tests/test_dossier.py` (**guardrail: dossier_service rejects/omits any skill/gap/inconsistency conclusion lacking an evidence reference — no fabricated conclusions, FR-028**; inconsistencies neutral; full upload→dossier flow; audit entries `cv_parsed`/`score_computed`/`dossier_generated` written)

**Checkpoint**: US1+US2 = demoable MVP — CV+vacancy → explainable, reproducible, evidence-based dossier.

---

## Phase 5: User Story 3 — Review dossier & record human decision (Priority: P2)

**Goal**: Recruiter records the final human decision; system never auto-decides.
**Independent test**: Record each decision type → persisted with actor, timestamp, AI recommendation
shown, human outcome; `decision_recorded` in audit; no automatic final outcome ever created.

- [ ] T049 [P] [US3] Create `app/models/decision.py` (Decision: actor_user_id, ai_recommendation, human_outcome `interview|review|discard`, note, decided_at)
- [ ] T050 [P] [US3] Create `app/schemas/decision.py`
- [ ] T051 [US3] [reuse:agentdesk] Create `app/services/decision_service.py` adapting the ticket approve/reject HITL pattern: human-only creation, records AI recommendation shown. Emit `decision_recorded`
- [ ] T052 [US3] Create `app/api/v1/decisions.py` (`POST /candidates/{id}/decision` [org_admin,recruiter], `GET /candidates/{id}/decision`)
- [ ] T053 [US3] Alembic migration `0005_decisions`
- [ ] T054 [P] [US3] Test: `tests/test_decision.py` (record decision persists all fields + audit; **no Decision/final outcome is ever created without an explicit human request** — FR-023)

**Checkpoint**: US3 closes the loop with human accountability + audit trail.

---

## Phase 6: User Story 4 — Export dossier to PDF (Priority: P3)

**Goal**: Recruiter exports the dossier (incl. recorded decision) to a shareable PDF.
**Independent test**: Export a generated dossier → PDF with all sections; `pdf_exported` in audit.

- [ ] T055 [US4] [new] Create `app/services/report_pdf.py` (render dossier → PDF via **ReportLab** for MVP; WeasyPrint deferred as future enhancement per research.md R7). Emit `pdf_exported`
- [ ] T056 [US4] Add `POST /candidates/{id}/dossier/export` to `app/api/v1/exports.py` → `application/pdf`
- [ ] T057 [P] [US4] Test: `tests/test_export.py` (PDF produced with dossier sections; `pdf_exported` audit entry)

**Checkpoint**: US4 adds shareable output.

---

## Phase 7: Retention & deletion (cross-cutting, privacy by design)

- [ ] T058 [new] Create `app/services/retention_service.py` (hard-delete candidate data on demand cascading document/consent/dossier/score/decisions; configurable TTL via `CANDIDATE_DATA_TTL_DAYS`)
- [ ] T059 Add `DELETE /candidates/{id}` [org_admin] to candidates router → 204
- [ ] T060 [P] Test: `tests/test_retention.py` (hard-delete removes all candidate-linked rows; cross-org delete → 404)

---

## Phase 8: Frontend — Recruiter dashboard (Next.js 15)

- [ ] T061 [P] Scaffold `frontend/` (Next.js 15 App Router, Tailwind v4, TS) with `lib/{api.ts,types.ts,auth.ts}`
- [ ] T062 [P] Login page + auth token handling (`frontend/app/login/page.tsx`)
- [ ] T063 Vacancies: list + create form (`frontend/app/(dashboard)/vacancies/`)
- [ ] T064 Candidate upload (CV + consent checkbox) UI (`frontend/app/(dashboard)/candidates/new/`)
- [ ] T065 [reuse:jobops] Dossier view adapting `ScoreCard` + new `Breakdown`, `EvidenceList`, `DossierView` components (`frontend/components/`) showing score, per-factor breakdown, skills+evidence, gaps, neutral inconsistencies, interview questions, non-binding recommendation
- [ ] T066 Decision panel (record interview/review/discard + note) + PDF export button
- [ ] T067 [P] Display a visible non-binding disclaimer and a fairness/consent notice in the dossier UI

**Checkpoint**: full recruiter flow demoable end-to-end in the browser.

---

## Phase 9: Polish & cross-cutting

- [ ] T068 [P] Backend `README.md` + frontend `README.md` (run, test, env) referencing quickstart.md
- [ ] T069 [P] Ensure structured logging + audit metadata (provider/model version, sources analyzed) on all five events
- [ ] T070 Run full suite `LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock pytest -q`; ruff + mypy clean; CI green
- [ ] T071 [P] End-to-end smoke per quickstart.md (login → vacancy → CV+consent → dossier → decision → PDF → audit)

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2)** block everything.
- **US1 (P3)** and the model/scaffolding of **US2 (P4)** can begin once Foundational is done; US2 scoring
  depends on US1's vacancy embedding being available for a real evaluation.
- **US3 (P5)** depends on a Dossier existing (US2).
- **US4 (P6)** depends on a Dossier (US2) and optionally a Decision (US3).
- **Retention (P7)** depends on the candidate entities (US2).
- **Frontend (P8)** depends on the corresponding backend endpoints per story.
- **Polish (P9)** last.

### Parallel opportunities

- Setup: T003, T004, T005, T006, T008 in parallel after T001/T002.
- Foundational: T013, T015, T016 in parallel; tests T020/T021 in parallel.
- US2 models T028–T032 in parallel; tests T034, T039, T040, T047, T048 in parallel once their targets exist.

## Implementation Strategy

- **MVP = US1 + US2** (Phases 1–4): a recruiter goes from CV + vacancy to an explainable, reproducible,
  evidence-based dossier — already demoable and sellable.
- Then layer **US3** (human decision + audit), **US4** (PDF), retention, and the frontend incrementally.
- Every phase closes with a change summary, file list, how-to-test, and a passing test run for the
  affected modules (constitution Development Workflow). A phase MUST NOT advance while critical errors
  remain.

## Reuse summary

- **[reuse:agentdesk]**: core/config/security/deps, rbac, db infra, providers, audit model+service,
  HITL decision pattern, workers, conftest. (T006–T009, T012–T017, T044, T051)
- **[reuse:jobops]**: scoring weights/components, scoring_service breakdown+narrative, score model
  shape, ScoreCard frontend. (T031, T035, T036, T038, T065)
- **[new]**: cv_parser, fairness_guard, inconsistency_detector, interview_questions, report_pdf,
  retention_service. (T033, T037, T041, T042, T055, T058)
