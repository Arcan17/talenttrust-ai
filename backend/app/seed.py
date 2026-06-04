"""Seed an initial organization + recruiter user from settings, if absent.

Idempotent: safe to run on every startup. Used for local demos and the quickstart.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.db.engine import SessionLocal
from app.models.organization import Organization
from app.models.user import Role, User


async def seed(db: AsyncSession) -> None:
    existing = await db.scalar(
        select(User).where(func.lower(User.email) == settings.seed_user_email.lower())
    )
    if existing is not None:
        return

    org = await db.scalar(
        select(Organization).where(Organization.name == settings.seed_org_name)
    )
    if org is None:
        org = Organization(name=settings.seed_org_name)
        db.add(org)
        await db.flush()

    db.add(
        User(
            organization_id=org.id,
            email=settings.seed_user_email.lower(),
            hashed_password=hash_password(settings.seed_user_password),
            role=Role.recruiter,
        )
    )
    await db.commit()


async def run_seed() -> None:  # pragma: no cover - invoked from startup/CLI, not tests
    async with SessionLocal() as db:
        await seed(db)
