<!-- SPECKIT START -->
Active feature: **001-talenttrust-mvp** (TalentTrust AI — AI Candidate Dossier, MVP Phase 1).

For technologies, project structure, data model, contracts, and decisions, read:
- Plan: `specs/001-talenttrust-mvp/plan.md`
- Spec: `specs/001-talenttrust-mvp/spec.md`
- Data model: `specs/001-talenttrust-mvp/data-model.md`
- Contracts: `specs/001-talenttrust-mvp/contracts/openapi.md`
- Research: `specs/001-talenttrust-mvp/research.md`
- Quickstart: `specs/001-talenttrust-mvp/quickstart.md`
- Constitution: `.specify/memory/constitution.md`

Stack: Python 3.11 / FastAPI / SQLAlchemy 2.0 async / Pydantic v2 / PostgreSQL 16 + pgvector /
Celery + Redis / Next.js 15 + TS + Tailwind. LLM & embedding providers are behind interfaces with a
deterministic Mock default; never call real LLMs in tests/CI. The 0–100 score is deterministic and
reproducible — the LLM only explains it, never produces or alters the number. Reuse patterns from
`agentdesk-ai` (auth/RBAC, audit, HITL, providers, Celery, conftest) and `jobops-ai` (scoring engine).
<!-- SPECKIT END -->
