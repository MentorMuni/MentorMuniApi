"""Alembic: coding assessment domain (versioned problems, jobs, runs).

Revision ID: 0017_coding_assessment
Revises: 0016_company_intelligence

Seeds one practice assessment + Two Sum problem (pre-authored; no AI generation).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Allow importing app.coding.seed_mvp when alembic runs from mentormuni-api/
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.coding.seed_mvp import seed_mvp_coding_content  # noqa: E402

revision: str = "0017_coding_assessment"
down_revision: Union[str, None] = "0016_company_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coding_languages",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("judge0_language_id", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("file_extension", sa.String(length=16), nullable=False),
        sa.Column("time_multiplier", sa.Float(), nullable=False, server_default="1"),
        sa.Column("default_memory_limit_kb", sa.Integer(), nullable=True),
        sa.Column("starter_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_coding_languages_code"),
    )
    op.create_index("ix_coding_languages_code", "coding_languages", ["code"])

    op.create_table(
        "coding_problems",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("current_version_id", sa.BigInteger(), nullable=True),
        sa.Column("company_key", sa.String(length=160), nullable=True),
        sa.Column("company_name", sa.String(length=160), nullable=True),
        sa.Column("role_key", sa.String(length=160), nullable=True),
        sa.Column("role_name", sa.String(length=160), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column("topic", sa.String(length=80), nullable=True),
        sa.Column("subtopic", sa.String(length=80), nullable=True),
        sa.Column("pattern", sa.String(length=80), nullable=True),
        sa.Column("evidence_confidence", sa.Float(), nullable=True),
        sa.Column("evidence_notes", sa.Text(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_coding_problems_slug"),
    )
    op.create_index("ix_coding_problems_slug", "coding_problems", ["slug"])
    op.create_index("ix_coding_problems_status", "coding_problems", ["status"])
    op.create_index("ix_coding_problems_company_key", "coding_problems", ["company_key"])
    op.create_index("ix_coding_problems_difficulty", "coding_problems", ["difficulty"])
    op.create_index("ix_coding_problems_topic", "coding_problems", ["topic"])

    op.create_table(
        "coding_problem_versions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("problem_id", sa.BigInteger(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(length=32), nullable=False),
        sa.Column("topic", sa.String(length=80), nullable=True),
        sa.Column("subtopic", sa.String(length=80), nullable=True),
        sa.Column("pattern", sa.String(length=80), nullable=True),
        sa.Column("constraints_text", sa.Text(), nullable=True),
        sa.Column("input_format", sa.Text(), nullable=True),
        sa.Column("output_format", sa.Text(), nullable=True),
        sa.Column("examples_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("expected_time_complexity", sa.String(length=64), nullable=True),
        sa.Column("expected_space_complexity", sa.String(length=64), nullable=True),
        sa.Column("expected_approach", sa.Text(), nullable=True),
        sa.Column("concepts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("starter_code_by_language", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("weight_policy_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("time_limit_ms", sa.Integer(), nullable=True),
        sa.Column("memory_limit_kb", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_id"], ["coding_problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("problem_id", "version_number", name="uq_coding_problem_versions_problem_ver"),
    )
    op.create_index("ix_coding_problem_versions_problem_id", "coding_problem_versions", ["problem_id"])

    op.create_foreign_key(
        "fk_coding_problems_current_version",
        "coding_problems",
        "coding_problem_versions",
        ["current_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "coding_reference_solutions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("problem_version_id", sa.BigInteger(), nullable=False),
        sa.Column("language_code", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_version_id"], ["coding_problem_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("problem_version_id", "language_code", name="uq_coding_ref_sol_version_lang"),
    )
    op.create_index("ix_coding_reference_solutions_problem_version_id", "coding_reference_solutions", ["problem_version_id"])

    op.create_table(
        "coding_test_cases",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("problem_version_id", sa.BigInteger(), nullable=False),
        sa.Column("input", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["problem_version_id"], ["coding_problem_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_test_cases_problem_version_id", "coding_test_cases", ["problem_version_id"])
    op.create_index("ix_coding_test_cases_is_hidden", "coding_test_cases", ["is_hidden"])

    op.create_table(
        "coding_assessments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("company_key", sa.String(length=160), nullable=True),
        sa.Column("company_name", sa.String(length=160), nullable=True),
        sa.Column("role_key", sa.String(length=160), nullable=True),
        sa.Column("role_name", sa.String(length=160), nullable=True),
        sa.Column("difficulty", sa.String(length=32), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("allowed_languages_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='["python", "cpp", "java"]'),
        sa.Column("evidence_confidence", sa.Float(), nullable=True),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_coding_assessments_slug"),
    )
    op.create_index("ix_coding_assessments_slug", "coding_assessments", ["slug"])
    op.create_index("ix_coding_assessments_organization_id", "coding_assessments", ["organization_id"])
    op.create_index("ix_coding_assessments_company_key", "coding_assessments", ["company_key"])
    op.create_index("ix_coding_assessments_status", "coding_assessments", ["status"])

    op.create_table(
        "coding_assessment_problems",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_id", sa.BigInteger(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Float(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["coding_assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["coding_problems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assessment_id", "problem_id", name="uq_coding_assessment_problems_assessment_problem"),
    )
    op.create_index("ix_coding_assessment_problems_assessment_id", "coding_assessment_problems", ["assessment_id"])
    op.create_index("ix_coding_assessment_problems_problem_id", "coding_assessment_problems", ["problem_id"])

    op.create_table(
        "coding_attempts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["coding_assessments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_attempts_student_id", "coding_attempts", ["student_id"])
    op.create_index("ix_coding_attempts_assessment_id", "coding_attempts", ["assessment_id"])
    op.create_index("ix_coding_attempts_status", "coding_attempts", ["status"])

    op.create_table(
        "coding_attempt_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["coding_attempts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", name="uq_coding_attempt_snapshots_attempt_id"),
    )
    op.create_index("ix_coding_attempt_snapshots_attempt_id", "coding_attempt_snapshots", ["attempt_id"])

    op.create_table(
        "coding_attempt_problems",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_version_id", sa.BigInteger(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points", sa.Float(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["coding_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["coding_problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_version_id"], ["coding_problem_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "problem_version_id", name="uq_coding_attempt_problems_attempt_version"),
    )
    op.create_index("ix_coding_attempt_problems_attempt_id", "coding_attempt_problems", ["attempt_id"])
    op.create_index("ix_coding_attempt_problems_problem_id", "coding_attempt_problems", ["problem_id"])
    op.create_index("ix_coding_attempt_problems_problem_version_id", "coding_attempt_problems", ["problem_version_id"])

    op.create_table(
        "coding_drafts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_version_id", sa.BigInteger(), nullable=False),
        sa.Column("language_code", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["coding_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_version_id"], ["coding_problem_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("attempt_id", "problem_version_id", "language_code", name="uq_coding_drafts_attempt_version_lang"),
    )
    op.create_index("ix_coding_drafts_attempt_id", "coding_drafts", ["attempt_id"])
    op.create_index("ix_coding_drafts_problem_version_id", "coding_drafts", ["problem_version_id"])

    op.create_table(
        "coding_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_version_id", sa.BigInteger(), nullable=False),
        sa.Column("language_code", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("verdict", sa.String(length=64), nullable=True),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("memory_used_kb", sa.Integer(), nullable=True),
        sa.Column("result_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attempt_id"], ["coding_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_version_id"], ["coding_problem_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_runs_student_id", "coding_runs", ["student_id"])
    op.create_index("ix_coding_runs_attempt_id", "coding_runs", ["attempt_id"])
    op.create_index("ix_coding_runs_problem_version_id", "coding_runs", ["problem_version_id"])
    op.create_index("ix_coding_runs_source_hash", "coding_runs", ["source_hash"])
    op.create_index("ix_coding_runs_execution_status", "coding_runs", ["execution_status"])
    op.create_index("ix_coding_runs_created_at", "coding_runs", ["created_at"])

    op.create_table(
        "coding_submissions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("attempt_id", sa.BigInteger(), nullable=False),
        sa.Column("assessment_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_id", sa.BigInteger(), nullable=False),
        sa.Column("problem_version_id", sa.BigInteger(), nullable=False),
        sa.Column("language_code", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("execution_status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("verdict", sa.String(length=64), nullable=True),
        sa.Column("analysis_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("memory_used_kb", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attempt_id"], ["coding_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assessment_id"], ["coding_assessments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_id"], ["coding_problems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["problem_version_id"], ["coding_problem_versions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_submissions_student_id", "coding_submissions", ["student_id"])
    op.create_index("ix_coding_submissions_attempt_id", "coding_submissions", ["attempt_id"])
    op.create_index("ix_coding_submissions_assessment_id", "coding_submissions", ["assessment_id"])
    op.create_index("ix_coding_submissions_problem_id", "coding_submissions", ["problem_id"])
    op.create_index("ix_coding_submissions_problem_version_id", "coding_submissions", ["problem_version_id"])
    op.create_index("ix_coding_submissions_source_hash", "coding_submissions", ["source_hash"])
    op.create_index("ix_coding_submissions_execution_status", "coding_submissions", ["execution_status"])
    op.create_index("ix_coding_submissions_analysis_status", "coding_submissions", ["analysis_status"])
    op.create_index("ix_coding_submissions_created_at", "coding_submissions", ["created_at"])

    op.create_table(
        "coding_test_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("test_case_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("memory_used_kb", sa.Integer(), nullable=True),
        sa.Column("actual_output", sa.Text(), nullable=True),
        sa.Column("error_type", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["coding_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["coding_test_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", "test_case_id", name="uq_coding_test_results_submission_case"),
    )
    op.create_index("ix_coding_test_results_submission_id", "coding_test_results", ["submission_id"])
    op.create_index("ix_coding_test_results_test_case_id", "coding_test_results", ["test_case_id"])

    op.create_table(
        "coding_ai_analyses",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.BigInteger(), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False, server_default="coding_analysis_v1"),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("overall_coaching_score", sa.Float(), nullable=True),
        sa.Column("correctness_coaching_score", sa.Float(), nullable=True),
        sa.Column("approach_score", sa.Float(), nullable=True),
        sa.Column("complexity_score", sa.Float(), nullable=True),
        sa.Column("code_quality_score", sa.Float(), nullable=True),
        sa.Column("edge_case_score", sa.Float(), nullable=True),
        sa.Column("understood_constraints", sa.Boolean(), nullable=True),
        sa.Column("complexity_appropriate_for_constraints", sa.Boolean(), nullable=True),
        sa.Column("missed_scalable_approach", sa.Boolean(), nullable=True),
        sa.Column("constraint_notes", sa.Text(), nullable=True),
        sa.Column("detected_approach", sa.Text(), nullable=True),
        sa.Column("time_complexity", sa.String(length=64), nullable=True),
        sa.Column("space_complexity", sa.String(length=64), nullable=True),
        sa.Column("analysis_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["coding_submissions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", name="uq_coding_ai_analyses_submission_id"),
    )
    op.create_index("ix_coding_ai_analyses_submission_id", "coding_ai_analyses", ["submission_id"])

    op.create_table(
        "coding_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("student_id", sa.BigInteger(), nullable=True),
        sa.Column("attempt_id", sa.BigInteger(), nullable=True),
        sa.Column("submission_id", sa.BigInteger(), nullable=True),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_submission_token", sa.String(length=128), nullable=True),
        sa.Column("provider_status", sa.String(length=64), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["attempt_id"], ["coding_attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["submission_id"], ["coding_submissions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["coding_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coding_jobs_job_type", "coding_jobs", ["job_type"])
    op.create_index("ix_coding_jobs_status", "coding_jobs", ["status"])
    op.create_index("ix_coding_jobs_student_id", "coding_jobs", ["student_id"])
    op.create_index("ix_coding_jobs_attempt_id", "coding_jobs", ["attempt_id"])
    op.create_index("ix_coding_jobs_submission_id", "coding_jobs", ["submission_id"])
    op.create_index("ix_coding_jobs_run_id", "coding_jobs", ["run_id"])
    op.create_index("ix_coding_jobs_next_retry_at", "coding_jobs", ["next_retry_at"])
    op.create_index("ix_coding_jobs_created_at", "coding_jobs", ["created_at"])

    seed_mvp_coding_content()


def downgrade() -> None:
    op.drop_table("coding_jobs")
    op.drop_table("coding_ai_analyses")
    op.drop_table("coding_test_results")
    op.drop_table("coding_submissions")
    op.drop_table("coding_runs")
    op.drop_table("coding_drafts")
    op.drop_table("coding_attempt_problems")
    op.drop_table("coding_attempt_snapshots")
    op.drop_table("coding_attempts")
    op.drop_table("coding_assessment_problems")
    op.drop_table("coding_assessments")
    op.drop_table("coding_test_cases")
    op.drop_table("coding_reference_solutions")
    op.drop_constraint("fk_coding_problems_current_version", "coding_problems", type_="foreignkey")
    op.drop_table("coding_problem_versions")
    op.drop_table("coding_problems")
    op.drop_table("coding_languages")
