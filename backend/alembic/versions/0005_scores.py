"""scores

Revision ID: 0005_scores
Revises: 0004_candidates_documents_consents
Create Date: 2026-06-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_scores"
down_revision: str | None = "0004_candidates_documents_consents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "recommendation",
            sa.Enum(
                "high_priority_interview",
                "good_review_gaps",
                "needs_human_review",
                "low_fit",
                name="score_recommendation",
            ),
            nullable=False,
        ),
        sa.Column("breakdown", _JSONB, nullable=False),
        sa.Column("narrative", _JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_scores_organization_id", "scores", ["organization_id"])
    op.create_index("ix_scores_candidate_id", "scores", ["candidate_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_scores_candidate_id", table_name="scores")
    op.drop_index("ix_scores_organization_id", table_name="scores")
    op.drop_table("scores")
    op.execute("DROP TYPE IF EXISTS score_recommendation")
