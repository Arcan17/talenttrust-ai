"""User — a member of one organization with a role.

Roles (Constitution Principle VIII): `org_admin`, `recruiter`, `viewer`.
`viewer` is read-only; only `org_admin`/`recruiter` may create vacancies or record
decisions (enforced per-endpoint via `require_role`).
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Role(enum.StrEnum):
    org_admin = "org_admin"
    recruiter = "recruiter"
    viewer = "viewer"


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_user_org_email"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="user_role"), nullable=False, default=Role.recruiter
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
