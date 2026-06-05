"""Aggregates all v1 routers. Domain routers (vacancies, candidates, dossiers,
decisions, exports) are added in later phases."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, candidates, health, scores, users, vacancies

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(vacancies.router)
api_router.include_router(candidates.router)
api_router.include_router(scores.router)
