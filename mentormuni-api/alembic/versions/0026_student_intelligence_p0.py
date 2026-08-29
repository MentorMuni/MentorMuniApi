"""Student Intelligence P0 tables (portal only).

Revision ID: 0026_student_intelligence_p0
Revises: 0025_individual_student_profile

Note: Contract used UUID ids; this codebase uses BigInteger PKs/FKs matching users.id.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_student_intelligence_p0"
down_revision: Union[str, None] = "0025_individual_student_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_attempt",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("tool_code", sa.String(length=50), nullable=True),
        sa.Column("widget_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("topic_nodes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("modality", sa.String(length=20), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("accuracy", sa.Numeric(5, 4), nullable=True),
        sa.Column("time_taken_s", sa.Integer(), nullable=True),
        sa.Column("technical_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("communication_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("mistakes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("item_embeddings", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("transcript_ref", sa.String(length=64), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_student_attempt_student_date",
        "student_attempt",
        ["student_id", sa.text("completed_at DESC")],
    )

    op.create_table(
        "student_topic_mastery",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic_id", sa.String(length=100), nullable=False),
        sa.Column("recognition_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recognition_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recognition_last_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "recognition_consecutive_passes",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("application_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("application_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("application_last_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "application_consecutive_passes",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("explanation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explanation_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("explanation_last_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "explanation_consecutive_passes",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("student_id", "topic_id", name="uq_student_topic_mastery"),
    )
    op.create_index("idx_topic_mastery_student", "student_topic_mastery", ["student_id"])
    op.create_index(
        "idx_topic_mastery_due",
        "student_topic_mastery",
        ["student_id", "next_review_at"],
    )

    op.create_table(
        "student_coverage_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic_id", sa.String(length=100), nullable=False),
        sa.Column("pool", sa.String(length=10), nullable=False, server_default="NEW"),
        sa.Column("first_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "never_return_to_new",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("student_id", "topic_id", name="uq_student_coverage_topic"),
    )
    op.create_index("idx_coverage_student", "student_coverage_ledger", ["student_id"])
    op.create_index(
        "idx_coverage_pool",
        "student_coverage_ledger",
        ["student_id", "pool"],
    )

    op.create_table(
        "student_memory",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fact_type", sa.String(length=50), nullable=False),
        sa.Column("topic_id", sa.String(length=100), nullable=True),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("evidence_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_observed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_student_memory_student", "student_memory", ["student_id"])
    op.create_index(
        "idx_student_memory_active",
        "student_memory",
        ["student_id", "resolved_at"],
        postgresql_where=sa.text("resolved_at IS NULL"),
    )

    op.create_table(
        "student_target",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_companies",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "target_tier",
            sa.String(length=50),
            nullable=False,
            server_default="mass_recruiter",
        ),
        sa.Column("target_readiness", sa.Integer(), nullable=False, server_default="85"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("student_id", name="uq_student_target_student"),
    )

    op.create_table(
        "student_readiness_snapshot",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("overall", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("base", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("execution_multiplier", sa.Numeric(4, 2), nullable=False, server_default="1"),
        sa.Column("coverage", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("measured_pillars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_pillars", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("eta_days", sa.Integer(), nullable=True),
        sa.Column("pillars", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("focus_pillar", sa.String(length=50), nullable=True),
        sa.Column("weakest_pillar", sa.String(length=50), nullable=True),
        sa.Column("gates", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "student_id",
            "snapshot_date",
            name="uq_student_readiness_snapshot_day",
        ),
    )
    op.create_index(
        "idx_readiness_snapshot_student_date",
        "student_readiness_snapshot",
        ["student_id", sa.text("snapshot_date DESC")],
    )

    op.create_table(
        "student_mission_anchor",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_id", sa.BigInteger(), nullable=True),
        sa.Column("anchor_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("student_id", "plan_id", name="uq_student_mission_anchor"),
    )

    op.create_table(
        "student_daily_task_ledger",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan_id", sa.BigInteger(), nullable=True),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("task_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("score", sa.Numeric(5, 2), nullable=True),
        sa.Column("text_hash", sa.String(length=64), nullable=True),
        sa.Column("widget_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("why_this", sa.Text(), nullable=True),
        sa.Column("skill_demand_score", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "student_id",
            "plan_id",
            "local_date",
            "task_key",
            name="uq_student_daily_task",
        ),
    )
    op.create_index(
        "idx_daily_task_student_date",
        "student_daily_task_ledger",
        ["student_id", "local_date"],
    )

    op.create_table(
        "student_daily_activity",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "student_id",
            sa.BigInteger(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("tasks_done", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tasks_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_rate_7d", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("student_id", "local_date", name="uq_student_daily_activity"),
    )


def downgrade() -> None:
    op.drop_table("student_daily_activity")
    op.drop_table("student_daily_task_ledger")
    op.drop_table("student_mission_anchor")
    op.drop_table("student_readiness_snapshot")
    op.drop_table("student_target")
    op.drop_table("student_memory")
    op.drop_table("student_coverage_ledger")
    op.drop_table("student_topic_mastery")
    op.drop_table("student_attempt")
