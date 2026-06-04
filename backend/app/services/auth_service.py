"""Authentication business logic: registration, login, token refresh.

`register` creates a new organization with an `org_admin` user (self-serve onboarding).
Login/refresh return a token pair. Audit events are emitted by the router layer.
"""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.organization import Organization
from app.models.user import Role, User
from app.schemas.auth import TokenPair


class AuthError(Exception):
    """Raised on invalid credentials or tokens."""


class ConflictError(Exception):
    """Raised when an organization or user already exists."""


def _token_pair(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.organization_id, user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


async def register(
    db: AsyncSession, *, organization_name: str, email: str, password: str
) -> tuple[TokenPair, User]:
    existing_org = await db.scalar(
        select(Organization).where(Organization.name == organization_name)
    )
    if existing_org is not None:
        raise ConflictError("Organization name already taken")

    org = Organization(name=organization_name)
    db.add(org)
    await db.flush()

    user = User(
        organization_id=org.id,
        email=email.lower(),
        hashed_password=hash_password(password),
        role=Role.org_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _token_pair(user), user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> tuple[TokenPair, User]:
    user = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid credentials")
    return _token_pair(user), user


async def refresh(db: AsyncSession, *, refresh_token: str) -> TokenPair:
    from jose import JWTError

    try:
        payload = decode_token(refresh_token, "refresh")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise AuthError("Invalid refresh token") from exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("Invalid refresh token")
    return _token_pair(user)
