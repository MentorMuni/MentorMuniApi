"""Fix NULL plan_id uniqueness + embeddings type for student intelligence.

Revision ID: 0027_student_intelligence_uniques
Revises: 0026_student_intelligence_p0
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_student_intelligence_uniques"
down_revision: Union[str, None] = "0026_student_intelligence_p0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Deduplicate before unique indexes (keep lowest id).
    op.execute(
        """
        DELETE FROM student_mission_anchor a
        USING student_mission_anchor b
        WHERE a.id > b.id
          AND a.student_id = b.student_id
          AND a.plan_id IS NULL AND b.plan_id IS NULL
        """
    )
    op.execute(
        """
        DELETE FROM student_daily_task_ledger a
        USING student_daily_task_ledger b
        WHERE a.id > b.id
          AND a.student_id = b.student_id
          AND a.local_date = b.local_date
          AND a.task_key = b.task_key
          AND a.plan_id IS NULL AND b.plan_id IS NULL
        """
    )

    op.drop_constraint("uq_student_mission_anchor", "student_mission_anchor", type_="unique")
    op.create_index(
        "uq_student_mission_anchor_with_plan",
        "student_mission_anchor",
        ["student_id", "plan_id"],
        unique=True,
        postgresql_where=sa.text("plan_id IS NOT NULL"),
    )
    op.create_index(
        "uq_student_mission_anchor_no_plan",
        "student_mission_anchor",
        ["student_id"],
        unique=True,
        postgresql_where=sa.text("plan_id IS NULL"),
    )

    op.drop_constraint("uq_student_daily_task", "student_daily_task_ledger", type_="unique")
    op.create_index(
        "uq_student_daily_task_with_plan",
        "student_daily_task_ledger",
        ["student_id", "plan_id", "local_date", "task_key"],
        unique=True,
        postgresql_where=sa.text("plan_id IS NOT NULL"),
    )
    op.create_index(
        "uq_student_daily_task_no_plan",
        "student_daily_task_ledger",
        ["student_id", "local_date", "task_key"],
        unique=True,
        postgresql_where=sa.text("plan_id IS NULL"),
    )

    # Align embeddings column with Float[] (ORM)
    op.alter_column(
        "student_attempt",
        "item_embeddings",
        type_=postgresql.ARRAY(sa.Float()),
        postgresql_using="item_embeddings::double precision[]",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.drop_index("uq_student_daily_task_no_plan", table_name="student_daily_task_ledger")
    op.drop_index("uq_student_daily_task_with_plan", table_name="student_daily_task_ledger")
    op.create_unique_constraint(
        "uq_student_daily_task",
        "student_daily_task_ledger",
        ["student_id", "plan_id", "local_date", "task_key"],
    )

    op.drop_index("uq_student_mission_anchor_no_plan", table_name="student_mission_anchor")
    op.drop_index("uq_student_mission_anchor_with_plan", table_name="student_mission_anchor")
    op.create_unique_constraint(
        "uq_student_mission_anchor",
        "student_mission_anchor",
        ["student_id", "plan_id"],
    )

    op.alter_column(
        "student_attempt",
        "item_embeddings",
        type_=postgresql.ARRAY(sa.Numeric()),
        postgresql_using="item_embeddings::numeric[]",
        existing_nullable=True,
    )
