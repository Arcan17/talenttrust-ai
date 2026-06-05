"""add candidate_deleted to audit_event enum

Revision ID: 0008_audit_candidate_deleted
Revises: 0007_decisions
Create Date: 2026-06-04
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_audit_candidate_deleted"
down_revision: str | None = "0007_decisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL: extend the existing enum type. No-op on other dialects.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE audit_event ADD VALUE IF NOT EXISTS 'candidate_deleted'")


def downgrade() -> None:
    # PostgreSQL cannot easily drop a single enum value; intentionally a no-op.
    pass
