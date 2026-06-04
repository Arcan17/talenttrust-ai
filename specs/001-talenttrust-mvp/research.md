# Phase 0 Research: AI Candidate Dossier

All Technical Context unknowns are resolved below. No outstanding NEEDS CLARIFICATION remain (the five
open decisions were settled in `spec.md` → Clarifications, Session 2026-06-04).

## R1. CV text extraction (PDF/DOCX)

- **Decision**: PyMuPDF (`fitz`) for PDF text extraction; `python-docx` for DOCX. Reject files that
  are not PDF/DOCX, exceed 5 MB, or yield no extractable text (image-only/scanned PDFs).
- **Rationale**: Both are mature, pure-Python-friendly, fast, and offline. Rejecting no-text PDFs
  keeps the dossier evidence-based (no hallucinated content from empty input) and defers OCR to a
  later phase as the spec requires.
- **Alternatives considered**: `pdfminer.six` (slower, lower-level), Unstructured/`pdfplumber` (heavier
  deps); Tesseract OCR (explicitly out of scope for Phase 1).

## R2. LLM structuring of parsed text

- **Decision**: After deterministic text extraction, the LLM (via `LLMProvider`) structures the raw
  text into a Pydantic `ParsedCV` (education, experience with dates, skills, languages, certifications).
  The mock provider returns deterministic structured output for tests.
- **Rationale**: Honors Principle II (providers behind interfaces) and Principle IV (LLM never produces
  the score — it only structures/explains). Keeps CI offline and deterministic.
- **Alternatives considered**: Pure regex/heuristic parsing (brittle across CV layouts); a fine-tuned
  model (overkill for MVP).

## R3. Deterministic scoring engine (0–100, 6 factors)

- **Decision**: Port JobOps `scoring/weights.py` + `components.py`; invert orientation to
  candidate↔vacancy; emit a 0–100 score from six fixed-weight factors (skills 35, experience 20,
  seniority 15, modality/location 10, evidence 10, inconsistency penalty 10). Skills/experience/evidence
  use mock-deterministic embeddings (cosine); seniority/modality use rules. Persist the full breakdown;
  a test asserts the weighted components reconcile to the final value and that identical inputs yield
  identical output.
- **Rationale**: Directly satisfies Principles IV/V and FR-011..013; reuses a proven, tested engine.
- **Alternatives considered**: LLM-as-judge scoring (rejected — violates Principles IV/V); pure keyword
  matching (less robust than embedding similarity).

## R4. Fairness guard

- **Decision**: A pure function `fairness_guard.strip(features)` removes/blocks sensitive attributes
  (age, gender, nationality, marital status, health, religion, political affiliation, exact address)
  before any feature reaches the scoring engine. Unit test: mutating only a sensitive field leaves the
  score unchanged (SC-006).
- **Rationale**: Principle X; turns a legal/ethical requirement into a testable invariant.
- **Alternatives considered**: Post-hoc bias auditing only (insufficient — the data could still
  influence the number).

## R5. Inconsistency detection (7 signals, neutral language)

- **Decision**: Deterministic rules in `inconsistency_detector.py` over the structured `ParsedCV` and
  vacancy: overlapping/illogical dates, large gaps, seniority-vs-experience mismatch, skill-without-
  evidence, declared-language-vs-CV-language, incomplete/ambiguous education, certifications without
  verifiable detail. Output uses neutral "requires review" phrasing with an evidence reference.
- **Rationale**: FR-019; deterministic (no LLM) keeps results reproducible and defensible.
- **Alternatives considered**: LLM-detected inconsistencies (non-deterministic, risk of fabrication).

## R6. Interview-question generation

- **Decision**: `interview_questions.py` calls the LLM (provider interface) over the assembled dossier
  and gaps to suggest questions; purely explanatory, never feeding the score.
- **Rationale**: High-value, low-risk LLM use consistent with Principle IV.

## R7. PDF export

- **Decision (fixed for MVP)**: Use **ReportLab first** for the dossier PDF — pure-Python, no system
  dependencies, easy to test deterministically in CI. WeasyPrint (HTML/CSS template) is deferred as a
  **future enhancement** only if the recruiter-facing report needs richer HTML/CSS layout. Emits
  `pdf_exported`.
- **Rationale**: ReportLab keeps the Phase-1 build dependency-light and the CI image simple (WeasyPrint
  needs Cairo/Pango system libs). The dossier layout is straightforward (sections + a score table), so
  ReportLab covers it without HTML rendering.
- **Alternatives considered**: WeasyPrint-first (heavier deploy deps — deferred); headless-Chrome PDF
  (heavy runtime); client-side PDF (loses server-side audit of the export event).

## R8. Multi-tenant auth, RBAC, audit, HITL, async jobs, test harness

- **Decision**: Reuse AgentDesk patterns wholesale — org-scoped entities, JWT+refresh, `require_role`,
  append-only `audit_service`, the `ticket_service` approve/reject/transition pattern adapted into a
  `decision_service`, Celery+Redis with an eager flag for tests, and the `conftest.py` mock-provider/
  in-memory-SQLite fixtures.
- **Rationale**: These are solved, tested problems in a sibling codebase; reuse de-risks the build and
  satisfies Principles VI/VII/VIII/IX and Principle III's deterministic-CI requirement.

## R9. Retention & deletion

- **Decision**: Hard-delete endpoint for a candidate's data on demand; a configurable env TTL
  (`CANDIDATE_DATA_TTL_DAYS`, default 180); no mandatory auto-purge job in Phase 1.
- **Rationale**: FR-027 / Principle VI privacy-by-design without over-building a purge scheduler now.
