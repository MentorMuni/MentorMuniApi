"""Add progress learning topics cache on student_roadmap_weeks.

Revision ID: 0014_progress_topics
Revises: 0013_student_roadmap
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_progress_topics"
down_revision: Union[str, None] = "0013_student_roadmap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student_roadmap_weeks",
        sa.Column(
            "progress_topics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "student_roadmap_weeks",
        sa.Column(
            "progress_topics_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("student_roadmap_weeks", "progress_topics_at")
    op.drop_column("student_roadmap_weeks", "progress_topics_json")
