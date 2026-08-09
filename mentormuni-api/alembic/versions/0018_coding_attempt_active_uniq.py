"""Partial unique index: one in_progress attempt per student+assessment."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0018_coding_attempt_active_uniq"
down_revision: Union[str, None] = "0017_coding_assessment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_coding_attempts_active_student_assessment
        ON coding_attempts (student_id, assessment_id)
        WHERE status = 'in_progress'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_coding_attempts_active_student_assessment")
