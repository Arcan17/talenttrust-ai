# TalentTrust AI — Frontend

Recruiter dashboard (Next.js 15 + TypeScript + Tailwind v4) for the TalentTrust AI backend.

## Status (Phase 8a)

Implemented: auth (login, session via localStorage, `GET /auth/me`, logout), protected dashboard
layout with a visible non-binding-recommendation disclaimer, and vacancy management (list, create,
detail). CV upload, candidate/dossier/score/decision views and PDF export arrive in Phase 8b.

## Setup

```bash
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL (default http://localhost:8000)
npm install
npm run dev                        # http://localhost:3000
```

The backend must be running (see `../backend/README.md`). Quick start:

```bash
# backend (in ../backend)
docker compose up --build          # or run uvicorn locally
# create an org + org_admin to log in with:
curl -s localhost:8000/api/v1/auth/register \
  -H 'content-type: application/json' \
  -d '{"organization_name":"Acme","email":"admin@acme.com","password":"supersecret1"}'
```

Then log in at http://localhost:3000/login.

## Checks

```bash
npm run lint        # ESLint (next/core-web-vitals + next/typescript)
npm run typecheck   # tsc --noEmit
npm run build       # production build
```
