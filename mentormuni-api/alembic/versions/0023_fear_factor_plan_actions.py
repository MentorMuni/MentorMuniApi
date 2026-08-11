"""Fear factor live score, plan-action completions, weekly checkin_id.

Revision ID: 0023_fear_factor_plan_actions
Revises: 0022_platform_support_tickets
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023_fear_factor_plan_actions"
down_revision: Union[str, None] = "0022_platform_support_tickets"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "private_student_fear_solutions",
        sa.Column("current_severity", sa.Integer(), nullable=True),
    )
    op.add_column(
        "private_student_weekly_progress",
        sa.Column("checkin_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "idx_private_weekly_progress_checkin",
        "private_student_weekly_progress",
        ["checkin_id"],
    )

    op.create_table(
        "private_student_plan_actions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("checkin_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("fear_id", sa.String(length=128), nullable=False),
        sa.Column("tool_code", sa.String(length=64), nullable=False),
        sa.Column("action_key", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "checkin_id",
            "fear_id",
            "tool_code",
            name="uq_private_plan_action_checkin_fear_tool",
        ),
    )
    op.create_index(
        "idx_private_plan_actions_student",
        "private_student_plan_actions",
        ["student_id", "checkin_id"],
    )
    op.create_index(
        "ix_private_student_plan_actions_checkin_id",
        "private_student_plan_actions",
        ["checkin_id"],
    )
    op.create_index(
        "ix_private_student_plan_actions_student_id",
        "private_student_plan_actions",
        ["student_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_private_student_plan_actions_student_id",
        table_name="private_student_plan_actions",
    )
    op.drop_index(
        "ix_private_student_plan_actions_checkin_id",
        table_name="private_student_plan_actions",
    )
    op.drop_index(
        "idx_private_plan_actions_student",
        table_name="private_student_plan_actions",
    )
    op.drop_table("private_student_plan_actions")
    op.drop_index(
        "idx_private_weekly_progress_checkin",
        table_name="private_student_weekly_progress",
    )
    op.drop_column("private_student_weekly_progress", "checkin_id")
    op.drop_column("private_student_fear_solutions", "current_severity")
