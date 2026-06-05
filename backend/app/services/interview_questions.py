"""Interview-question generation — grounded in detected gaps, skills and inconsistencies.

Questions are derived deterministically from concrete dossier items (missing required skills,
neutral inconsistencies, and skills actually present in the CV). They never assert facts that
are not in the CV/vacancy — each question carries the evidence it is based on. The provider
abstraction (mock by default) remains available for optional phrasing, but the grounding is
deterministic so nothing is fabricated.
"""
from __future__ import annotations

_MAX_QUESTIONS = 8


def _ev(source: str, detail: str) -> dict:
    return {"source": source, "detail": detail}


def generate(
    *,
    missing_required_skills: list[str],
    present_required_skills: list[str],
    inconsistencies: list[dict],
) -> list[dict]:
    questions: list[dict] = []

    # From gaps (missing required skills) — ask the candidate to evidence them.
    for skill in missing_required_skills:
        questions.append({
            "question": (
                f"El cargo requiere {skill}. ¿Puedes describir tu experiencia concreta con {skill} "
                f"y un proyecto donde lo hayas aplicado?"
            ),
            "rationale": f"{skill} es obligatoria para la vacante y no se evidenció en el CV.",
            "based_on": "gap",
            "evidence": [
                _ev("vacancy", f"Skill obligatoria: {skill}"),
                _ev("cv", "Skill no detectada en el documento"),
            ],
        })

    # From inconsistencies — invite the candidate to clarify (neutral).
    for item in inconsistencies:
        questions.append({
            "question": (
                f"Sobre '{item['signal']}': {item['message']} ¿Puedes aportar detalles que ayuden "
                f"a validarlo?"
            ),
            "rationale": "Punto marcado para revisión en el dossier.",
            "based_on": "inconsistency",
            "evidence": list(item.get("evidence", [])) or [_ev("system_rule", "Señal de revisión")],
        })

    # From present required skills — deepen verified strengths.
    for skill in present_required_skills:
        questions.append({
            "question": (
                f"Veo {skill} en tu CV. ¿Cómo lo has usado en producción y qué decisiones técnicas "
                f"tomaste?"
            ),
            "rationale": f"{skill} aparece como evidencia en el CV y es relevante para el cargo.",
            "based_on": "skill",
            "evidence": [
                _ev("cv", f"{skill} detectada en el CV"),
                _ev("vacancy", f"{skill} relevante para el cargo"),
            ],
        })

    return questions[:_MAX_QUESTIONS]
