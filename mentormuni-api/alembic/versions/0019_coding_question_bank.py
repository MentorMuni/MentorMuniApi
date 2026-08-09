"""Alembic: coding question bank pipeline (generation lifecycle + relevance).

Does NOT change student execution tables semantics.
Student APIs continue to serve only status=published problems.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_coding_question_bank"
down_revision: Union[str, None] = "0018_coding_attempt_active_uniq"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("coding_problems", sa.Column("prompt_version", sa.String(length=64), nullable=True))
    op.add_column("coding_problems", sa.Column("generation_model", sa.String(length=64), nullable=True))
    op.add_column("coding_problems", sa.Column("generation_run_id", sa.BigInteger(), nullable=True))
    op.add_column("coding_problems", sa.Column("quality_score", sa.Float(), nullable=True))
    op.add_column(
        "coding_problems",
        sa.Column("validation_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column("coding_problems", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("coding_problems", sa.Column("approved_by", sa.String(length=160), nullable=True))
    op.add_column("coding_problems", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("coding_problems", sa.Column("rejected_reason", sa.Text(), nullable=True))
    op.add_column("coding_problems", sa.Column("content_fingerprint", sa.String(length=64), nullable=True))
    op.create_index("ix_coding_problems_prompt_version", "coding_problems", ["prompt_version"])
    op.create_index("ix_coding_problems_generation_run_id", "coding_problems", ["generation_run_id"])
    op.create_index("ix_coding_problems_content_fingerprint", "coding_problems", ["content_fingerprint"])

    op.add_column("coding_problem_versions", sa.Column("explanation_text", sa.Text(), nullable=True))
    op.add_column(
        "coding_problem_versions",
        sa.Column(
            "supported_languages_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default='["python", "cpp", "java"]',
            nullable=False,
        ),
    )
    op.add_column(
        "coding_problem_versions",
        sa.Column("generation_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.add_column("coding_test_cases", sa.Column("category", sa.String(length=64), nullable=True))
    op.create_index("ix_coding_test_cases_category", "coding_test_cases", ["category"])

    op.create_table(
        "coding_generation_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("curriculum_version", sa.String(length=64), server_default="placement_v1", nullable=False),
        sa.Column("target_count", sa.Integer(), server_default="50", nullable=False),
        sa.Column("generated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=160), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_generation_runs_status", "coding_generation_runs", ["status"])
    op.create_index("ix_coding_generation_runs_created_at", "coding_generation_runs", ["created_at"])

    op.create_table(
        "coding_problem_relevances",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("problem_id", sa.BigInteger(), nullable=False),
        sa.Column("company_key", sa.String(length=160), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=True),
        sa.Column("role_key", sa.String(length=160), server_default="software-engineer", nullable=False),
        sa.Column("role_name", sa.String(length=160), nullable=True),
        sa.Column("round_key", sa.String(length=64), server_default="coding", nullable=False),
        sa.Column("relevance", sa.String(length=32), server_default="medium", nullable=False),
        sa.Column("evidence_confidence", sa.Float(), nullable=True),
        sa.Column("evidence_notes", sa.Text(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["coding_problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "problem_id",
            "company_key",
            "role_key",
            "round_key",
            name="uq_coding_problem_relevances_tuple",
        ),
    )
    op.create_index("ix_coding_problem_relevances_problem_id", "coding_problem_relevances", ["problem_id"])
    op.create_index("ix_coding_problem_relevances_company_key", "coding_problem_relevances", ["company_key"])

    op.create_table(
        "coding_validation_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("problem_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_version_id", sa.BigInteger(), nullable=True),
        sa.Column("generation_run_id", sa.BigInteger(), nullable=True),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("checks_json", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("errors_json", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("duplicate_of_problem_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["coding_problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_version_id"], ["coding_problem_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generation_run_id"], ["coding_generation_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_validation_results_problem_id", "coding_validation_results", ["problem_id"])
    op.create_index("ix_coding_validation_results_verdict", "coding_validation_results", ["verdict"])
    op.create_index("ix_coding_validation_results_created_at", "coding_validation_results", ["created_at"])


def downgrade() -> None:
    op.drop_table("coding_validation_results")
    op.drop_table("coding_problem_relevances")
    op.drop_table("coding_generation_runs")
    op.drop_index("ix_coding_test_cases_category", table_name="coding_test_cases")
    op.drop_column("coding_test_cases", "category")
    op.drop_column("coding_problem_versions", "generation_payload_json")
    op.drop_column("coding_problem_versions", "supported_languages_json")
    op.drop_column("coding_problem_versions", "explanation_text")
    op.drop_index("ix_coding_problems_content_fingerprint", table_name="coding_problems")
    op.drop_index("ix_coding_problems_generation_run_id", table_name="coding_problems")
    op.drop_index("ix_coding_problems_prompt_version", table_name="coding_problems")
    for col in (
        "content_fingerprint",
        "rejected_reason",
        "published_at",
        "approved_by",
        "approved_at",
        "validation_summary_json",
        "quality_score",
        "generation_run_id",
        "generation_model",
        "prompt_version",
    ):
        op.drop_column("coding_problems", col)
