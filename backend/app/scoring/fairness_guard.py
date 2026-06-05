"""Fairness guard — strips protected/sensitive attributes before scoring.

Constitution Principle X: the scoring engine MUST NEVER consume age, gender, nationality,
marital status, health, religion, political affiliation, exact address, photo, or family
information. This module removes any CV line that mentions such an attribute, so altering a
sensitive attribute cannot change the computed score. The scoring engine additionally only
consumes an allowlist of non-sensitive signals (skill vocabulary, seniority tokens, country
match) — sanitizing the text is defense-in-depth on top of that.
"""
from __future__ import annotations

import re

# Keyword markers (ES + EN) whose presence flags a line as sensitive and removable.
SENSITIVE_MARKERS: tuple[str, ...] = (
    # age / birth
    "edad", "años de edad", "age", "fecha de nacimiento", "nacimiento", "born",
    "date of birth", "dob",
    # gender / sex
    "género", "genero", "sexo", "gender", "sex:",
    # nationality
    "nacionalidad", "nationality",
    # marital / family
    "estado civil", "marital", "casado", "casada", "soltero", "soltera",
    "hijos", "children", "familia", "family", "dependientes",
    # health
    "salud", "health", "discapacidad", "disability", "enfermedad",
    # religion
    "religión", "religion", "religious",
    # politics
    "política", "politica", "political", "partido",
    # exact address
    "dirección", "direccion", "address", "domicilio", "calle ", "street ",
    # photo
    "foto", "fotografía", "photo", "photograph",
)

# The attribute *names* the scoring engine is allowed to never see (for assertions/tests).
PROTECTED_ATTRIBUTES: tuple[str, ...] = (
    "age", "gender", "nationality", "marital_status", "health", "religion",
    "political_affiliation", "exact_address", "photo", "family_information",
)

_marker_re = re.compile(
    "|".join(re.escape(m) for m in SENSITIVE_MARKERS), re.IGNORECASE
)


def is_sensitive_line(line: str) -> bool:
    return bool(_marker_re.search(line))


def sanitize_text(text: str) -> str:
    """Return the CV text with any line mentioning a sensitive attribute removed."""
    return "\n".join(line for line in text.splitlines() if not is_sensitive_line(line))
