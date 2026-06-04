# Phase 1 Data Model: AI Candidate Dossier

All entities use the shared `UUIDMixin` (UUID PK) and `TimestampMixin` (`created_at`, `updated_at`),
reused from AgentDesk `app/db/base.py`. Every tenant-scoped table carries `organization_id`
(FK → `organizations.id`, indexed, cascade delete) and is queried filtered by the authenticated user's
organization. Vector columns use the portable `Embedding` type (pgvector on Postgres, JSON fallback on
SQLite).

## Entities

### Organization
- `name: str`
- Relationships: 1–N User, Vacancy, Candidate, AuditLogEntry.

### User
- `organization_id: FK`
- `email: str` (unique per org — `uq_user_org_email`)
- `hashed_password: str`
- `role: enum{org_admin, recruiter, viewer}`
- `is_active: bool`
- Rules: `viewer` cannot create vacancies or record decisions; only `org_admin`/`recruiter` may.

### Vacancy
- `organization_id: FK`
- `title: str` (required), `description: text`
- `required_skills: JSON[str]` (required, ≥1), `desired_skills: JSON[str]`
- `modality: enum{remote, hybrid, onsite}`
- `country: str`, `salary_min: int|null`, `salary_max: int|null`
- `seniority: enum{junior, mid, senior}`
- `requirements_embedding: Embedding` (over required+desired skills, for scoring)
- Relationships: 1–N Candidate (candidates evaluated against this vacancy).

### Candidate
- `organization_id: FK`, `vacancy_id: FK`
- `display_name: str|null` (from CV; professional identity only)
- `status: enum{received, analyzed}` (operational, NOT a hiring outcome)
- Relationships: 1–1 CandidateDocument, 1–N Consent, 0–1 Dossier, 0–N Decision.
- Deletion: hard-delete cascades document, consent, dossier, score, decisions (FR-027).

### CandidateDocument
- `organization_id: FK`, `candidate_id: FK`
- `filename: str`, `content_type: enum{pdf, docx}`, `size_bytes: int` (≤ 5_242_880)
- `sha256: str`, `raw_text: text` (extracted), `parsed: JSON` (`ParsedCV`)
- Validation: reject non-pdf/docx, >5 MB, or empty `raw_text` (image-only/no-text) → error, no dossier.

### Consent
- `organization_id: FK`, `candidate_id: FK`
- `version: str`, `scope: str` (what will be analyzed), `granted_at: datetime`, `granted_by_user_id: FK`
- Rule: at least one valid Consent MUST exist before analysis (FR-008/009). Append-only (versioned).

### Dossier
- `organization_id: FK`, `candidate_id: FK` (unique), `vacancy_id: FK`
- `summary: text` (LLM, evidence-based)
- `skills: JSON[ {name, evidence[]} ]` — each conclusion carries ≥1 evidence reference
- `gaps: JSON[ {requirement, note} ]`
- `inconsistencies: JSON[ {signal, detail, evidence, severity} ]` (neutral language)
- `interview_questions: JSON[str]`
- `recommendation: enum{interview, review, low_fit}` — explicitly **non-binding**
- Relationships: 1–1 Score.
- Invariant: no item in `skills`/`gaps`/`inconsistencies` may be persisted without an evidence ref.

### Score
- `organization_id: FK`, `dossier_id: FK` (unique)
- `value: int` (0–100)
- `breakdown: JSON[ {factor, weight, sub_score, weighted} ]` where factors are the six fixed-weight
  components (skills 35, experience 20, seniority 15, modality_location 10, evidence 10,
  inconsistency_penalty 10); Σ weighted reconciles to `value` within rounding.
- `narrative: JSON{ rationale, risks[], missing_requirements[] }` (LLM; never alters `value`)
- Invariant: `value` computed deterministically; identical (CandidateDocument.parsed, Vacancy) →
  identical `value` + `breakdown`.

### Decision
- `organization_id: FK`, `candidate_id: FK`, `actor_user_id: FK`
- `ai_recommendation: enum{interview, review, low_fit}` (the recommendation shown at decision time)
- `human_outcome: enum{interview, review, discard}`
- `note: text|null`, `decided_at: datetime`
- Rule: created ONLY by a human action; the system never writes a final outcome automatically (FR-023).

### AuditLogEntry (immutable, append-only — reused from AgentDesk)
- `organization_id: FK|null`, `actor_user_id: FK|null`
- `event: enum` extended with `cv_parsed, dossier_generated, score_computed, decision_recorded,
  pdf_exported` (plus existing `login_success, login_failed`)
- `target_type: str`, `target_id: str`, `meta: JSON` (e.g. provider/model version, sources analyzed),
  `created_at: datetime`
- No update/delete operations.

## Key Relationships

```
Organization 1─N User
Organization 1─N Vacancy 1─N Candidate 1─1 CandidateDocument
Candidate 1─N Consent
Candidate 0─1 Dossier 1─1 Score
Candidate 0─N Decision
Organization 1─N AuditLogEntry
```

## Lifecycle / State

- Candidate.status: `received` → (after successful parse + dossier) `analyzed`. These are operational
  states only; they are NOT hiring outcomes and never change automatically into a final decision.
- A hiring outcome exists ONLY as a `Decision` row created by a human (FR-023).
