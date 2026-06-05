"""Phase 4b-i — deterministic scoring engine, breakdown, fairness (unit tests)."""
from __future__ import annotations

import asyncio

from app.models.score import Recommendation
from app.models.vacancy import Modality, Seniority, Vacancy
from app.providers.factory import get_embedding_provider
from app.scoring import components as C
from app.scoring import fairness_guard
from app.scoring import weights as W
from app.services import scoring_service


def _vacancy(required=("python", "fastapi"), desired=("docker",), seniority=Seniority.mid):
    return Vacancy(
        organization_id=None,
        title="Python Backend Developer",
        description="APIs",
        required_skills=list(required),
        desired_skills=list(desired),
        modality=Modality.remote,
        country="CL",
        seniority=seniority,
    )


def _embed(text: str) -> list[float]:
    return asyncio.run(get_embedding_provider().embed([text]))[0]


def _score(vacancy, candidate_skills, text):
    return scoring_service.compute_score(
        vacancy=vacancy,
        candidate_skills=candidate_skills,
        candidate_skills_embedding=_embed(" ".join(candidate_skills) or "none"),
        requirements_embedding=_embed(" ".join(vacancy.required_skills + vacancy.desired_skills)),
        sanitized_text=fairness_guard.sanitize_text(text),
    )


STRONG_CV = (
    "Senior Software Engineer. Experience building APIs with Python, FastAPI, "
    "Docker and PostgreSQL. 6 years of work."
)
WEAK_CV = "Sales associate. Experience in retail and customer service."


def test_weights_sum_to_100():
    assert W.get_weights().total == 100.0


def test_breakdown_reconciles_to_value():
    value, breakdown, _ = _score(_vacancy(), ["python", "fastapi", "docker"], STRONG_CV)
    weighted_sum = sum(item["weighted"] for item in breakdown)
    assert abs(weighted_sum - value) <= 0.5


def test_score_is_in_range_and_int():
    value, _, _ = _score(_vacancy(), ["python", "fastapi"], STRONG_CV)
    assert isinstance(value, int)
    assert 0 <= value <= 100


def test_score_is_reproducible():
    a = _score(_vacancy(), ["python", "fastapi", "docker"], STRONG_CV)
    b = _score(_vacancy(), ["python", "fastapi", "docker"], STRONG_CV)
    assert a[0] == b[0]
    assert a[1] == b[1]
    assert a[2] == b[2]


def test_relevant_skills_score_higher_than_irrelevant():
    strong, *_ = _score(_vacancy(), ["python", "fastapi", "docker"], STRONG_CV)
    weak, *_ = _score(_vacancy(), [], WEAK_CV)
    assert strong > weak


def test_recommendation_never_reject():
    for cv, skills in ((STRONG_CV, ["python", "fastapi", "docker"]), (WEAK_CV, [])):
        _, _, rec = _score(_vacancy(), skills, cv)
        assert rec in set(Recommendation)
        assert rec != "reject"  # type: ignore[comparison-overlap]


def test_sensitive_attributes_do_not_change_score():
    base = _score(_vacancy(), ["python", "fastapi", "docker"], STRONG_CV)
    sensitive = STRONG_CV + (
        "\nEdad: 45 años\nGénero: masculino\nNacionalidad: chilena\n"
        "Estado civil: casado\nReligión: católica\nAfiliación política: independiente\n"
        "Dirección: Calle Falsa 123, Santiago\nFoto adjunta\nHijos: 2"
    )
    altered = _score(_vacancy(), ["python", "fastapi", "docker"], sensitive)
    assert altered[0] == base[0]
    assert altered[1] == base[1]


def test_fairness_guard_strips_sensitive_lines():
    text = "Python developer\nEdad: 30\nFastAPI expert\nReligión: ninguna"
    cleaned = fairness_guard.sanitize_text(text)
    assert "Python developer" in cleaned
    assert "FastAPI expert" in cleaned
    assert "Edad" not in cleaned
    assert "Religión" not in cleaned


def test_cosine_bounds():
    assert C.cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert C.cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert C.cosine(None, [1.0]) == 0.0
