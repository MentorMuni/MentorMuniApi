"""DEPARTMENT_ADMIN titles: HOD / PLACEMENT_COORDINATOR (same access).

Revision ID: 0015_dept_admin_title
Revises: 0014_progress_topics
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_dept_admin_title"
down_revision: Union[str, None] = "0014_progress_topics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("dept_admin_title", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_users_dept_admin_title", "users", ["dept_admin_title"])

    # Existing department mentors become primary HOD.
    op.execute(
        """
        UPDATE users AS u
        SET dept_admin_title = 'HOD'
        FROM roles AS r
        WHERE u.role_id = r.id
          AND r.role_code = 'DEPARTMENT_ADMIN'
          AND u.dept_admin_title IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_dept_admin_title", table_name="users")
    op.drop_column("users", "dept_admin_title")
