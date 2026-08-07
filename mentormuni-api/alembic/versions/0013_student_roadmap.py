"""Student Week-1 roadmap + assessment results + generated 90-day plans.

Revision ID: 0013_student_roadmap
Revises: 0012_upcoming_drives
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_student_roadmap"
down_revision: Union[str, None] = "0012_upcoming_drives"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_roadmap_weeks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="in_progress"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_number", name="uq_student_roadmap_weeks_user_week"),
    )
    op.create_index("ix_student_roadmap_weeks_user_id", "student_roadmap_weeks", ["user_id"])

    op.create_table(
        "student_roadmap_steps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("week_id", sa.BigInteger(), nullable=False),
        sa.Column("tool_code", sa.String(length=64), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="locked"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("technical_score", sa.Integer(), nullable=True),
        sa.Column("communication_score", sa.Integer(), nullable=True),
        sa.Column(
            "strengths_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "weaknesses_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recommendations_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("latest_result_id", sa.BigInteger(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["week_id"], ["student_roadmap_weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("week_id", "tool_code", name="uq_student_roadmap_steps_week_tool"),
    )
    op.create_index("ix_student_roadmap_steps_week_id", "student_roadmap_steps", ["week_id"])
    op.create_index("ix_student_roadmap_steps_tool_code", "student_roadmap_steps", ["tool_code"])

    op.create_table(
        "student_assessment_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("week_id", sa.BigInteger(), nullable=False),
        sa.Column("step_id", sa.BigInteger(), nullable=False),
        sa.Column("tool_code", sa.String(length=64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("technical_score", sa.Integer(), nullable=True),
        sa.Column("communication_score", sa.Integer(), nullable=True),
        sa.Column(
            "strengths_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "weaknesses_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recommendations_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="roadmap"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["week_id"], ["student_roadmap_weeks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["student_roadmap_steps.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_student_assessment_results_user_tool",
        "student_assessment_results",
        ["user_id", "tool_code"],
    )
    op.create_index(
        "ix_student_assessment_results_user_created",
        "student_assessment_results",
        ["user_id", "created_at"],
    )
    op.create_index("ix_student_assessment_results_step_id", "student_assessment_results", ["step_id"])

    op.create_table(
        "student_generated_roadmaps",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("week_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="generating"),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column(
            "prompt_version",
            sa.String(length=64),
            nullable=False,
            server_default="placement_90day_v1",
        ),
        sa.Column("input_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("plan_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["week_id"], ["student_roadmap_weeks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_student_generated_roadmaps_user_created",
        "student_generated_roadmaps",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_student_generated_roadmaps_user_created", table_name="student_generated_roadmaps")
    op.drop_table("student_generated_roadmaps")
    op.drop_index("ix_student_assessment_results_step_id", table_name="student_assessment_results")
    op.drop_index("ix_student_assessment_results_user_created", table_name="student_assessment_results")
    op.drop_index("ix_student_assessment_results_user_tool", table_name="student_assessment_results")
    op.drop_table("student_assessment_results")
    op.drop_index("ix_student_roadmap_steps_tool_code", table_name="student_roadmap_steps")
    op.drop_index("ix_student_roadmap_steps_week_id", table_name="student_roadmap_steps")
    op.drop_table("student_roadmap_steps")
    op.drop_index("ix_student_roadmap_weeks_user_id", table_name="student_roadmap_weeks")
    op.drop_table("student_roadmap_weeks")
