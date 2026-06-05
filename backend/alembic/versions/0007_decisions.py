"""decisions

Revision ID: 0007_decisions
Revises: 0006_dossiers
Create Date: 2026-06-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_decisions"
down_revision: str | None = "0006_dossiers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

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
        "decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "human_outcome",
            sa.Enum("interview", "review", "reject", "hold", name="decision_outcome"),
            nullable=False,
        ),
        sa.Column("ai_recommendation", _RECOMMENDATION, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_decisions_organization_id", "decisions", ["organization_id"])
    op.create_index("ix_decisions_candidate_id", "decisions", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_decisions_candidate_id", table_name="decisions")
    op.drop_index("ix_decisions_organization_id", table_name="decisions")
    op.drop_table("decisions")
    op.execute("DROP TYPE IF EXISTS decision_outcome")
