"""candidates, candidate_documents, consents

Revision ID: 0004_candidates_documents_consents
Revises: 0003_vacancies
Create Date: 2026-06-04
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_candidates_documents_consents"
down_revision: str | None = "0003_vacancies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSONB = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vacancy_id", sa.Uuid(), sa.ForeignKey("vacancies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("status", sa.Enum("received", "analyzed", name="candidate_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_candidates_organization_id", "candidates", ["organization_id"])
    op.create_index("ix_candidates_vacancy_id", "candidates", ["vacancy_id"])

    op.create_table(
        "candidate_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.Enum("pdf", "docx", name="document_type"), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("parsed", _JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_candidate_documents_organization_id", "candidate_documents", ["organization_id"])
    op.create_index("ix_candidate_documents_candidate_id", "candidate_documents", ["candidate_id"])

    op.create_table(
        "consents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("granted_by_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_consents_organization_id", "consents", ["organization_id"])
    op.create_index("ix_consents_candidate_id", "consents", ["candidate_id"])


def downgrade() -> None:
    op.drop_index("ix_consents_candidate_id", table_name="consents")
    op.drop_index("ix_consents_organization_id", table_name="consents")
    op.drop_table("consents")
    op.drop_index("ix_candidate_documents_candidate_id", table_name="candidate_documents")
    op.drop_index("ix_candidate_documents_organization_id", table_name="candidate_documents")
    op.drop_table("candidate_documents")
    op.drop_index("ix_candidates_vacancy_id", table_name="candidates")
    op.drop_index("ix_candidates_organization_id", table_name="candidates")
    op.drop_table("candidates")
    op.execute("DROP TYPE IF EXISTS candidate_status")
    op.execute("DROP TYPE IF EXISTS document_type")
