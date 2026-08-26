"""Optional college profile fields for individual (PUBLIC) students.

Revision ID: 0025_individual_student_profile
Revises: 0024_student_whiteboard
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_individual_student_profile"
down_revision: Union[str, None] = "0024_student_whiteboard"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("college_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("course_or_branch", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "course_or_branch")
    op.drop_column("users", "college_name")
