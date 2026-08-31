"""Baseline sprint anchor date on student_target.

Revision ID: 0031_baseline_sprint_start
Revises: 0030_student_target_personalization
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0031_baseline_sprint_start"
down_revision: Union[str, None] = "0030_student_target_personalization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student_target",
        sa.Column("baseline_sprint_start_date", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("student_target", "baseline_sprint_start_date")
