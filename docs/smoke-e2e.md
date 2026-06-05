# End-to-end smoke test

[`scripts/smoke_e2e.sh`](../scripts/smoke_e2e.sh) drives the entire MVP flow against a running
backend and fails fast if any step misbehaves. It is **idempotent** (unique org/email per run via a
timestamp) and **offline** (the backend must use `LLM_PROVIDER=mock EMBEDDING_PROVIDER=mock`).

## Run

```bash
# 1) start the backend on :8000 with mock providers (Docker Compose or uvicorn)
# 2) then:
BASE=http://localhost:8000 ./scripts/smoke_e2e.sh
```

It uses the bundled [`scripts/sample_cv.pdf`](../scripts/sample_cv.pdf) (a small text-based CV).

## Steps validated & expected output

| # | Step | Endpoint | Expected |
|---|------|----------|----------|
| 1 | Register org_admin | `POST /auth/register` | 201, access token returned |
| 2 | Login | `POST /auth/login` | 200 |
| 3 | Create vacancy | `POST /vacancies` | 201, vacancy id |
| 4 | Upload candidate (CV + consent) | `POST /vacancies/{id}/candidates` | 201, candidate id |
| 5 | Generate dossier | `POST /candidates/{id}/dossier` | 201, `recommendation` present |
| 6 | Get score | `GET /candidates/{id}/score` | 200, `value` in 0–100 |
| 7 | Record human decision | `POST /candidates/{id}/decision` | 201, `human_outcome=interview` |
| 8 | Export PDF | `POST /candidates/{id}/dossier/export` | 200, body starts with `%PDF` |

Expected console output (values vary by run):

```
→ Backend: http://localhost:8000
1) register org_admin (admin+1733420000@smoke.test.example)
   OK (token len 295)
2) login
   OK (200)
3) create vacancy
   OK (vacancy 89552269-...)
4) upload candidate (CV + consent)
   OK (candidate eb442c6d-...)
5) generate dossier
   OK (recommendation=high_priority_interview)
6) get score
   OK (score=96/100)
7) record human decision
   OK (human_outcome=interview)
8) export dossier PDF
   OK (http=200, 4221 bytes, magic=%PDF)

SMOKE E2E PASSED
```

The script exits non-zero on the first failed step, so it is safe to use as a manual gate before a
demo. (It is intentionally not wired into CI, which already covers the same guarantees with 97
deterministic unit/integration tests.)
