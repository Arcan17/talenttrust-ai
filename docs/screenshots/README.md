# Screenshots (to capture)

Real screenshots are not yet committed. Capture the following from a running instance
(backend on :8000 with mock providers + frontend on :3000) and drop the PNGs in this folder,
then reference them from the root `README.md`.

| File | Screen | What it should show |
|------|--------|---------------------|
| `01-login.png` | Login | The login form at `/login`. |
| `02-vacancies-list.png` | Vacancies list | `/vacancies` with the create form and at least one vacancy. |
| `03-vacancy-detail-upload.png` | Vacancy detail + CV upload | `/vacancies/{id}` with the "Subir candidato" form (file + consent checkbox). |
| `04-candidate-dossier.png` | Candidate dossier | `/candidates/{id}` showing summary, skills-with-evidence, gaps, inconsistencies, questions. |
| `05-score-breakdown.png` | Score breakdown | The score card with the 0–100 value and the per-factor breakdown table. |
| `06-human-decision.png` | Human decision | The decision panel (interview/review/reject/hold + note) with the disclaimer visible. |
| `07-pdf-export.png` | PDF export | The exported dossier PDF (or the export button + resulting file). |

Suggested capture flow: run `./scripts/smoke_e2e.sh` once to seed data, then walk the UI.

Keep images < 500 KB where possible (PNG, ~1440px wide). Do not commit fabricated/mocked images —
only real captures.
