"""Extend student_target with placement onboarding personalization fields.

Revision ID: 0030_student_target_personalization
Revises: 0029_org_logo
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_student_target_personalization"
down_revision: Union[str, None] = "0029_org_logo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student_target",
        sa.Column(
            "starting_level",
            sa.String(length=32),
            nullable=False,
            server_default="some_experience",
        ),
    )
    op.add_column(
        "student_target",
        sa.Column("baseline_path", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "student_target",
        sa.Column("daily_budget_minutes", sa.Integer(), nullable=False, server_default="25"),
    )
    op.add_column(
        "student_target",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("student_target", "onboarding_completed_at")
    op.drop_column("student_target", "daily_budget_minutes")
    op.drop_column("student_target", "baseline_path")
    op.drop_column("student_target", "starting_level")
