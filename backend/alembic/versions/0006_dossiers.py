"""dossiers

Revision ID: 0006_dossiers
Revises: 0005_scores
Create Date: 2026-06-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_dossiers"
down_revision: str | None = "0005_scores"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

# Reuse the existing enum type created in 0005_scores (do not recreate it).
_RECOMMENDATION = postgresql.ENUM(
    "high_priority_interview",
    "good_review_gaps",
    "needs_human_review",
    "low_fit",
    name="score_recommendation",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "dossiers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("vacancy_id", sa.Uuid(), sa.ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary", _JSONB, nullable=False),
        sa.Column("skills", _JSONB, nullable=False),
        sa.Column("gaps", _JSONB, nullable=False),
        sa.Column("inconsistencies", _JSONB, nullable=False),
        sa.Column("interview_questions", _JSONB, nullable=False),
        sa.Column("recommendation", _RECOMMENDATION, nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_dossiers_organization_id", "dossiers", ["organization_id"])
    op.create_index("ix_dossiers_candidate_id", "dossiers", ["candidate_id"], unique=True)
    op.create_index("ix_dossiers_vacancy_id", "dossiers", ["vacancy_id"])


def downgrade() -> None:
    op.drop_index("ix_dossiers_vacancy_id", table_name="dossiers")
    op.drop_index("ix_dossiers_candidate_id", table_name="dossiers")
    op.drop_index("ix_dossiers_organization_id", table_name="dossiers")
    op.drop_table("dossiers")
