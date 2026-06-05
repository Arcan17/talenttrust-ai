"""vacancies

Revision ID: 0003_vacancies
Revises: 0002_org_user_audit
Create Date: 2026-06-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0003_vacancies"
down_revision: str | None = "0002_org_user_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.create_table(
        "vacancies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "required_skills",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "desired_skills",
            sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("modality", sa.Enum("remote", "hybrid", "onsite", name="vacancy_modality"), nullable=False),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("seniority", sa.Enum("junior", "mid", "senior", name="vacancy_seniority"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("open", "closed", name="vacancy_status"),
            nullable=False,
            server_default="open",
        ),
        sa.Column("requirements_embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_vacancies_organization_id", "vacancies", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_vacancies_organization_id", table_name="vacancies")
    op.drop_table("vacancies")
    op.execute("DROP TYPE IF EXISTS vacancy_modality")
    op.execute("DROP TYPE IF EXISTS vacancy_seniority")
    op.execute("DROP TYPE IF EXISTS vacancy_status")
