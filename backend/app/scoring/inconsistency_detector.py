"""Inconsistency detector — deterministic, neutral-language review flags.

Implements the seven Phase-1 signals (FR-019). Output NEVER uses accusatory language; it only
uses neutral phrasing ("requiere revisión", "no se encontró evidencia suficiente", "conviene
validar en entrevista"). Each item cites evidence. No LLM, no fabrication: a signal is raised
only from concrete, observable gaps between the CV and the vacancy.
"""
from __future__ import annotations

import re

from app.models.vacancy import Seniority, Vacancy
from app.scoring import components as C

NEUTRAL_REQUIRES_REVIEW = "requiere revisión"
NEUTRAL_NO_EVIDENCE = "no se encontró evidencia suficiente"
NEUTRAL_VALIDATE = "conviene validar en entrevista"

_SENIORITY_ORDER = {Seniority.junior: 0, Seniority.mid: 1, Seniority.senior: 2}

_CERT_TOKENS = ("certified", "certification", "certificación", "certificado", "certificate")
_SALARY_TOKENS = ("salario", "sueldo", "pretensión", "pretension", "salary", "expectativa")
_ENGLISH_REQUIRED_TOKENS = ("english", "inglés", "ingles")
_ENGLISH_EVIDENCE_TOKENS = ("english", "inglés", "ingles", "fluent", "advanced english")
_URL_OR_ID_RE = re.compile(r"https?://|credential|id[:#]|\b[A-Z0-9]{6,}\b")


def _ev(source: str, detail: str) -> dict:
    return {"source": source, "detail": detail}


def _norm(items: list[str]) -> set[str]:
    return {s.strip().lower() for s in items if s and s.strip()}


def _sub_score(breakdown: list[dict], factor: str) -> float:
    for item in breakdown:
        if item.get("factor") == factor:
            return float(item.get("sub_score", 0.0))
    return 0.0


def detect(
    *,
    vacancy: Vacancy,
    parsed: dict,
    sanitized_text: str,
    breakdown: list[dict],
) -> list[dict]:
    """Return a list of InconsistencyItem-shaped dicts (neutral language)."""
    text = sanitized_text.lower()
    candidate_skills = _norm(list(parsed.get("skills", [])))
    char_count = int(parsed.get("char_count", len(sanitized_text)))
    items: list[dict] = []

    # 1. Experiencia declarada insuficiente o ambigua.
    if _sub_score(breakdown, "experience_relevant") < 0.5:
        items.append({
            "signal": "experience_insufficient_or_ambiguous",
            "message": f"La experiencia relevante para el cargo {NEUTRAL_REQUIRES_REVIEW}.",
            "severity": "medium",
            "evidence": [
                _ev("score_breakdown", "Factor de experiencia relevante por debajo de 0.5"),
                _ev("cv", "El CV no evidencia experiencia clara en las skills requeridas"),
            ],
        })

    # 2. Seniority no respaldado por evidencia.
    inferred = C.infer_candidate_seniority(sanitized_text)
    if _SENIORITY_ORDER[inferred] < _SENIORITY_ORDER[vacancy.seniority]:
        items.append({
            "signal": "seniority_unsupported",
            "message": (
                f"El seniority esperado ({vacancy.seniority.value}) {NEUTRAL_NO_EVIDENCE} "
                f"en el CV; {NEUTRAL_VALIDATE}."
            ),
            "severity": "medium",
            "evidence": [
                _ev("vacancy", f"Seniority esperado: {vacancy.seniority.value}"),
                _ev("cv", f"Seniority inferido desde el CV: {inferred.value}"),
            ],
        })

    # 3. Skills obligatorias ausentes.
    required_norm = _norm(vacancy.required_skills)
    missing = sorted(required_norm - candidate_skills)
    if missing:
        items.append({
            "signal": "required_skills_missing",
            "message": (
                f"Skills obligatorias sin evidencia en el CV: {', '.join(missing)}. "
                f"{NEUTRAL_VALIDATE}."
            ),
            "severity": "high",
            "evidence": [
                _ev("vacancy", f"Skills obligatorias: {', '.join(sorted(required_norm))}"),
                _ev("cv", "No se detectaron estas skills en el documento"),
            ],
        })

    # 4. Idiomas requeridos no evidenciados.
    vacancy_text = (
        f"{vacancy.title} {vacancy.description} {' '.join(vacancy.required_skills)}"
    ).lower()
    if any(tok in vacancy_text for tok in _ENGLISH_REQUIRED_TOKENS):
        if not any(tok in text for tok in _ENGLISH_EVIDENCE_TOKENS):
            lang_msg = f"El idioma requerido (inglés) {NEUTRAL_NO_EVIDENCE}; {NEUTRAL_VALIDATE}."
            items.append({
                "signal": "required_language_not_evidenced",
                "message": lang_msg,
                "severity": "medium",
                "evidence": [
                    _ev("vacancy", "La vacante menciona inglés como requisito"),
                    _ev("cv", "El CV no evidencia inglés"),
                ],
            })

    # 5. Certificaciones mencionadas pero no verificables.
    if any(tok in text for tok in _CERT_TOKENS) and not _URL_OR_ID_RE.search(sanitized_text):
        items.append({
            "signal": "certifications_unverifiable",
            "message": (
                f"Se mencionan certificaciones sin detalle verificable; {NEUTRAL_REQUIRES_REVIEW}."
            ),
            "severity": "low",
            "evidence": [
                _ev("cv", "Certificación mencionada sin identificador o enlace verificable")
            ],
        })

    # 6. Salario/rango no informado cuando la vacante lo requiere.
    if (vacancy.salary_min is not None or vacancy.salary_max is not None) and not any(
        tok in text for tok in _SALARY_TOKENS
    ):
        items.append({
            "signal": "salary_expectation_missing",
            "message": (
                f"La vacante define un rango salarial y el CV {NEUTRAL_NO_EVIDENCE} sobre "
                f"pretensión de renta; {NEUTRAL_VALIDATE}."
            ),
            "severity": "low",
            "evidence": [
                _ev("vacancy", "La vacante define un rango salarial"),
                _ev("cv", "El CV no informa pretensión de renta"),
            ],
        })

    # 7. CV con baja evidencia estructurada.
    if char_count < 200 or len(candidate_skills) <= 1:
        detail = (
            f"Longitud del texto: {char_count} caracteres; "
            f"skills detectadas: {len(candidate_skills)}"
        )
        items.append({
            "signal": "low_structured_evidence",
            "message": f"El CV presenta baja evidencia estructurada; {NEUTRAL_REQUIRES_REVIEW}.",
            "severity": "low",
            "evidence": [_ev("cv", detail)],
        })

    return items
