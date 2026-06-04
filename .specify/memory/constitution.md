<!--
SYNC IMPACT REPORT
==================
Version change: (none) → 1.0.0
Bump rationale: Initial ratification of the TalentTrust AI constitution (first concrete
                version replacing the unfilled template). Adapted from the AgentDesk AI
                constitution and extended with recruiting-specific guardrails (evidence-based
                scoring, deterministic score / LLM-explains-only, human-final-decision, and
                fairness + consent by design).
Modified principles: N/A (initial definition)
Added sections:
  - Core Principles (I–X)
  - Additional Constraints: Technology & Security Standards
  - Development Workflow & Quality Gates
  - Governance
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ reviewed (Constitution Check gate is generic; aligns)
  - .specify/templates/spec-template.md ✅ reviewed (no mandated section conflicts)
  - .specify/templates/tasks-template.md ✅ reviewed (testing/observability task types covered)
Deferred TODOs: none
-->

# TalentTrust AI Constitution

TalentTrust AI is a human-in-the-loop B2B recruiting copilot. It turns a candidate CV (PDF/DOCX)
plus a structured job vacancy into a **verifiable, explainable candidate dossier**: an evidence-based
fit score, a professional summary, detected skills, gaps, neutral inconsistencies, suggested
interview questions, and a non-binding recommendation that a human recruiter records the final
decision on. TalentTrust AI is **NOT** a background-check or criminal-records search tool. This
constitution defines the non-negotiable engineering and ethical principles for the project. It exists
to keep the codebase clean, secure, deterministic, legally cautious, and demonstrably
production-grade.

## Core Principles

### I. Evidence-Based Scoring (NON-NEGOTIABLE)
Every materially important conclusion about a candidate MUST cite its source. A skill, strength, gap,
or inconsistency surfaced to the recruiter MUST be traceable to concrete evidence (e.g. a CV section,
a declared field, the vacancy requirements). The system MUST NOT present an unsourced claim such as
"good candidate" or "the AI said 82"; it MUST instead show the evidence and the per-factor breakdown
behind the number. Rationale: defensibility and trust are the product's core value — a recruiter and,
if challenged, a regulator must be able to see why any statement was made.

### II. Providers Behind Interfaces (NON-NEGOTIABLE)
All LLM and embedding access MUST go through abstract interfaces (`LLMProvider`, `EmbeddingProvider`).
Concrete adapters (Anthropic, OpenAI, Mock) are selected by environment variable. A deterministic
`MockProvider` is the default and the ONLY provider exercised in tests and CI. No business, scoring,
parsing, or agent code may import a vendor SDK directly. Rationale: vendor lock-in is avoided, costs
are controlled, and the system is testable without network or paid APIs.

### III. Deterministic Tests, No Paid APIs in CI (NON-NEGOTIABLE)
Tests MUST be deterministic and reproducible. There MUST be zero real LLM/embedding calls in CI; the
mock provider is forced via `LLM_PROVIDER=mock` and `EMBEDDING_PROVIDER=mock`. Every feature ships
with tests covering its happy path and key failure modes. Required coverage areas: auth/RBAC, CV
parsing, scoring (including breakdown reconciliation and reproducibility), inconsistency detection,
fairness exclusion, interview-question generation, the candidate-decision human-in-the-loop flow,
audit logging, and PDF export. Rationale: CI must be free, fast, and never flaky due to external
services.

### IV. Deterministic Score, LLM Explains Only (NON-NEGOTIABLE)
The numeric fit score (0–100) MUST be computed by deterministic, rule- and embedding-based components
with fixed, documented weights. The LLM MUST NEVER produce or modify the numeric score; it may only
generate prose that explains an already-computed score and its breakdown. The persisted score record
MUST include the full per-factor breakdown such that the weighted components reconcile to the final
value. Rationale: scores that drive hiring decisions must be auditable, stable, and free of black-box
model drift.

### V. Reproducible Scoring
Given the same candidate inputs and the same vacancy, scoring MUST produce an identical numeric result
and breakdown under the mock provider. Scoring logic MUST NOT depend on wall-clock time, randomness,
or non-deterministic ordering. Rationale: a recruiter must be able to re-run an evaluation and defend
that the same inputs always yield the same result.

### VI. Security & Privacy by Design (NON-NEGOTIABLE)
Secrets MUST NEVER be hardcoded or committed; a complete `.env.example` documents every variable. All
external inputs MUST be validated with Pydantic v2. Authentication uses JWT; authorization uses
role-based access control enforced per endpoint. Candidate data (CV documents, parsed personal data)
MUST be access-controlled, retained only as long as needed, and deletable on request; consent is
captured and versioned before analysis. Errors MUST be handled and never leak stack traces, secrets,
or candidate PII to clients. Rationale: the platform processes personal data of real candidates and
must model a defensible privacy posture (e.g. Chile's Ley 21.719 and analogous regimes).

### VII. Observability & Immutable Audit Log
The system MUST emit structured logs. Security- and decision-critical events MUST be written to an
immutable, append-only audit log, including at minimum: `cv_parsed`, `dossier_generated`,
`score_computed`, `decision_recorded`, `pdf_exported`, plus `login_success` and `login_failed`. Each
audit entry MUST record actor, organization, target, timestamp, and relevant metadata (e.g. provider/
model version and sources analyzed). Rationale: AI-assisted hiring is under heightened regulatory
scrutiny for bias and transparency; every consequential action must be traceable and reconstructable.

### VIII. Multi-Tenant Isolation
Every tenant-scoped entity MUST belong to an `Organization`. Queries MUST be scoped by the
authenticated user's organization; no endpoint may return another organization's data. Roles are
`org_admin`, `recruiter`, and `viewer`, enforced per endpoint. Vacancies, candidates, documents,
dossiers, decisions, and audit logs are all tenant-scoped. Rationale: a SaaS platform must guarantee
tenants never see each other's candidate data.

### IX. Human-in-the-Loop, Human-Final-Decision (NON-NEGOTIABLE)
The system MUST NOT make or imply an automated hiring decision. AI output is a non-binding
recommendation only; it MUST NEVER auto-reject, auto-advance, or auto-rank a candidate as a final
outcome. A human MUST record the final decision, and that decision MUST capture the actor, timestamp,
the AI recommendation shown, and the human outcome. Rationale: both ethics and law (e.g. the right not
to be subject to decisions based solely on automated processing) require a human accountable for the
outcome.

### X. Fairness, Non-Discrimination & Consent by Design (NON-NEGOTIABLE)
The scoring engine MUST NEVER consume protected or sensitive attributes — including age, gender,
nationality, marital status, health, religion, political affiliation, or exact home address — and a
`fairness_guard` MUST exclude such fields from any feature that influences the score. The system MUST
NOT search criminal records by name, scrape sensitive personal data without permission, mix
homonymous identities, or fabricate conclusions; uncertain findings MUST use neutral language
("requires review"), never accusatory framing. Candidate consent for analysis MUST be captured and
versioned before processing. Rationale: avoiding discriminatory and opaque practices is both a legal
requirement and the product's central commercial differentiator.

## Additional Constraints: Technology & Security Standards

- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic migrations.
- Data: PostgreSQL 16 with the pgvector extension as the vector store (single database).
- Async/jobs: Celery with Redis as broker/result backend; CV analysis runs as bounded async jobs with
  an eager fallback for tests.
- Document parsing: PDF/DOCX extraction MUST live behind a dedicated parsing layer; the LLM only
  structures already-extracted text and MUST NOT be the source of the numeric score (Principle IV).
- Scoring: a fixed-weight, deterministic engine on a 0–100 scale; weights are centralized and
  documented; the persisted breakdown reconciles to the final value.
- Frontend: Next.js 15 with TypeScript and Tailwind.
- Infrastructure: Docker Compose MUST bring up the full stack locally (postgres+pgvector, redis,
  backend, worker, frontend).
- CI/CD: GitHub Actions running lint, type-check, and pytest with mock providers only.

## Development Workflow & Quality Gates

- Spec-driven development is mandatory: specify → clarify → plan → tasks → analyze → implement.
- Implementation proceeds in phases; a phase MUST NOT advance while critical errors remain.
- Each phase closes with: a summary of changes, the list of files created/modified, how to test it,
  and a passing test run for the affected modules.
- New behavior requires accompanying deterministic tests (Principle III).
- Code MUST be reasonably typed and endpoints documented (FastAPI/OpenAPI).
- No change may introduce a direct vendor SDK import outside the `providers` layer (Principle II), a
  hardcoded secret (Principle VI), an LLM-derived numeric score (Principle IV), or a sensitive
  attribute into the scoring path (Principle X).

## Governance

This constitution supersedes ad-hoc practices for TalentTrust AI. Amendments MUST be made by editing
this file, accompanied by a Sync Impact Report and a semantic version bump:
- MAJOR: removal or backward-incompatible redefinition of a principle.
- MINOR: a new principle or materially expanded guidance.
- PATCH: clarifications and wording fixes.

All implementation work and reviews MUST verify compliance with these principles. Any deviation MUST
be justified in writing within the relevant spec or plan. Runtime development guidance for AI agents
lives in the project `CLAUDE.md`.

**Version**: 1.0.0 | **Ratified**: 2026-06-04 | **Last Amended**: 2026-06-04
