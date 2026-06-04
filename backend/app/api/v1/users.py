"""User listing — org-scoped, org_admin only.

A minimal foundational endpoint that exercises RBAC (org_admin only) and multi-tenant
isolation (only the caller's organization's users are ever returned).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import Role, User
from app.rbac import require_role
from app.schemas.user import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(require_role(Role.org_admin)),
) -> list[User]:
    rows = await db.scalars(
        select(User).where(User.organization_id == current.organization_id)
    )
    return list(rows)
