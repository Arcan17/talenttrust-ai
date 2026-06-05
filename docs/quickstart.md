# Quickstart — TalentTrust AI

End-to-end walkthrough: from zero to an exported candidate dossier. Every step is offline and
deterministic (mock AI providers).

## 0. Prerequisites

- Docker + Docker Compose (recommended), or Python 3.11 + Node 20 to run locally.
- The backend uses mock providers by default — no API keys required.

## 1. Start the backend

```bash
cd backend
cp .env.example .env
docker compose up --build        # postgres+pgvector, redis, backend (from repo root)
```

Wait for the backend on http://localhost:8000 (docs at `/docs`). It runs migrations on startup.

> Without Docker: create a venv, `pip install ".[dev]"`, point `DATABASE_URL` at a local
> Postgres+pgvector, `alembic upgrade head`, then `uvicorn app.main:app --reload`.

## 2. Register an org_admin (self-serve)

```bash
curl -s localhost:8000/api/v1/auth/register \
  -H 'content-type: application/json' \
  -d '{"organization_name":"Acme","email":"admin@acme.com","password":"supersecret1"}'
# → {"access_token":"...","refresh_token":"...","token_type":"bearer"}
```

Save the `access_token` as `TOK` for the curl steps below:

```bash
TOK=$(curl -s localhost:8000/api/v1/auth/login -H 'content-type: application/json' \
  -d '{"email":"admin@acme.com","password":"supersecret1"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

## 3. Run the frontend

```bash
cd frontend
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev                        # http://localhost:3000
```

Log in at http://localhost:3000/login with `admin@acme.com` / `supersecret1`.

You can do steps 4–8 from the UI, or via curl as shown.

## 4. Create a vacancy

UI: **Vacantes → Nueva vacante**. Or:

```bash
VID=$(curl -s -X POST localhost:8000/api/v1/vacancies -H "Authorization: Bearer $TOK" \
  -H 'content-type: application/json' \
  -d '{"title":"Python Backend Developer","required_skills":["python","fastapi"],
       "desired_skills":["docker"],"modality":"remote","country":"CL","seniority":"senior"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "$VID"
```

## 5. Upload a candidate CV (with consent)

UI: open the vacancy → **Subir candidato** (name, file PDF/DOCX, consent checkbox). Or:

```bash
CID=$(curl -s -X POST localhost:8000/api/v1/vacancies/$VID/candidates \
  -H "Authorization: Bearer $TOK" \
  -F "file=@scripts/sample_cv.pdf;type=application/pdf" \
  -F "consent_version=v1" -F "consent_scope=professional-evaluation" \
  -F "display_name=Jane Doe" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['id'])")
echo "$CID"
```

Consent is required — omitting it returns `422`. Non-PDF/DOCX → `400`, files >5 MB → `413`,
image-only/no-text PDFs → `400`.

## 6. Generate the dossier

UI: open the candidate → **Generar dossier**. Or:

```bash
curl -s -X POST localhost:8000/api/v1/candidates/$CID/dossier -H "Authorization: Bearer $TOK"
# → DossierOut: summary, skills (with evidence), gaps, inconsistencies, interview_questions, recommendation
```

## 7. View the score (0–100 + breakdown)

```bash
curl -s localhost:8000/api/v1/candidates/$CID/score -H "Authorization: Bearer $TOK"
# → {"value": <0-100>, "recommendation": "...", "breakdown": [ {factor, weight, sub_score, weighted}, ... ]}
```

The weighted components reconcile to `value`; the same inputs always yield the same score.

## 8. Record the human decision

UI: candidate page → **Decisión humana** (interview / review / reject / hold + note). Or:

```bash
curl -s -X POST localhost:8000/api/v1/candidates/$CID/decision -H "Authorization: Bearer $TOK" \
  -H 'content-type: application/json' \
  -d '{"human_outcome":"interview","note":"Strong fit"}'
# The AI recommendation is stored as context; the human outcome is the decision.
```

## 9. Export the dossier PDF

UI: candidate page → **Exportar dossier PDF**. Or:

```bash
curl -s -X POST localhost:8000/api/v1/candidates/$CID/dossier/export \
  -H "Authorization: Bearer $TOK" -o dossier.pdf
file dossier.pdf   # → PDF document
```

## 10. (Optional) Delete candidate data

```bash
curl -s -X DELETE localhost:8000/api/v1/candidates/$CID -H "Authorization: Bearer $TOK" -o /dev/null -w "%{http_code}\n"
# → 204; cascades document/consent/score/dossier/decisions; logs a PII-free candidate_deleted event
```

## One command for all of the above

```bash
BASE=http://localhost:8000 ./scripts/smoke_e2e.sh
```

See [`smoke-e2e.md`](smoke-e2e.md) for the expected output of each step.
