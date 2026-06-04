# API Contracts: AI Candidate Dossier (v1)

All endpoints are under `/api/v1`. All non-auth endpoints require a Bearer JWT and are scoped to the
caller's organization. Roles: `org_admin`, `recruiter` (write), `viewer` (read-only). Errors use a
consistent JSON shape `{ "detail": "<message>" }` and never leak stack traces or PII.

## Auth

- `POST /auth/login` — body `{ email, password }` → `{ access_token, refresh_token }`. Emits
  `login_success`/`login_failed`.
- `POST /auth/refresh` — body `{ refresh_token }` → `{ access_token }`.

## Vacancies

- `POST /vacancies` *(org_admin, recruiter)* — body `{ title, description, required_skills[],
  desired_skills[], modality, country, salary_min?, salary_max?, seniority }` → `201 VacancyOut`.
  `422` if required fields missing (FR-005).
- `GET /vacancies` — list org's vacancies → `200 [VacancyOut]`.
- `GET /vacancies/{id}` — `200 VacancyOut` | `404` (incl. cross-org).

## Candidates & CV upload

- `POST /vacancies/{vacancy_id}/candidates` *(org_admin, recruiter)* — multipart: `file` (PDF/DOCX,
  ≤5 MB) + `consent` `{ version, scope }`. Validates type/size/text; rejects with `400`/`413`/`422`.
  Creates Candidate + CandidateDocument + Consent, enqueues analysis. → `202 CandidateOut` (status
  `received`). Emits `cv_parsed` on successful extraction.
- `GET /candidates/{id}` — `200 CandidateOut` (status, has_dossier).
- `DELETE /candidates/{id}` *(org_admin)* — hard-delete candidate data (FR-027) → `204`.

## Dossier

- `POST /candidates/{id}/dossier` *(org_admin, recruiter)* — generate dossier (idempotent per
  candidate); `409` if no valid consent (FR-009). Runs fairness guard → scoring → inconsistency
  detection → interview questions → assembly. Emits `score_computed`, `dossier_generated`. →
  `200 DossierOut`.
- `GET /candidates/{id}/dossier` — `200 DossierOut` with `{ summary, score{value, breakdown[],
  narrative}, skills[{name, evidence[]}], gaps[], inconsistencies[], interview_questions[],
  recommendation }`. Every conclusion includes evidence (FR-017). `404` if not yet generated.

## Decision (human-in-the-loop)

- `POST /candidates/{id}/decision` *(org_admin, recruiter)* — body `{ human_outcome:
  interview|review|discard, note? }`. Server records `ai_recommendation` (as shown), actor, timestamp.
  Never auto-decides (FR-023/024). Emits `decision_recorded`. → `201 DecisionOut`.
- `GET /candidates/{id}/decision` — `200 DecisionOut | 404`.

## Export

- `POST /candidates/{id}/dossier/export` *(org_admin, recruiter)* — renders the dossier (incl. recorded
  decision if any) to PDF. Emits `pdf_exported`. → `200` `application/pdf`.

## Audit (read)

- `GET /audit` *(org_admin)* — list immutable audit entries for the org, filterable by `event`,
  `target_id` → `200 [AuditLogEntryOut]`.

## Health

- `GET /health` — `200 { status: "ok" }` (no auth).

## Contract Invariants (assertable in tests)

1. Cross-org access to any `{id}` resource returns `404`, never another org's data (Principle VIII).
2. `viewer` receives `403` on any write endpoint (Principle VIII / RBAC).
3. Dossier generation without a valid consent returns `409` (FR-009).
4. CV upload rejects non-PDF/DOCX (`400`), >5 MB (`413`), and no-text files (`400`) — no dossier
   created (FR-007/010).
5. Repeated `POST /dossier` for the same candidate+vacancy yields the same `score.value` and
   `breakdown` (Principle V / FR-012).
6. `score.breakdown` weighted components reconcile to `score.value` within rounding (FR-013).
7. No endpoint ever creates a `Decision` or final outcome without an explicit human `POST /decision`
   (Principle IX / FR-023).
8. Every successful `cv_parsed`/`dossier_generated`/`score_computed`/`decision_recorded`/`pdf_exported`
   action writes a matching immutable audit entry (FR-026).
