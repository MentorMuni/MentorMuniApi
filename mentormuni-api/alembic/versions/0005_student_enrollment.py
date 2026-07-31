"""
Student enrollment fields + invite-friendly columns.

Revision ID: 0005_student_enrollment
Revises: 0004_org_ops_notifications
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_student_enrollment"
down_revision: Union[str, None] = "0004_org_ops_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("roll_number", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("batch_year", sa.Integer(), nullable=True))
    op.create_index("ix_users_org_roll_number", "users", ["organization_id", "roll_number"])


def downgrade() -> None:
    op.drop_index("ix_users_org_roll_number", table_name="users")
    op.drop_column("users", "batch_year")
    op.drop_column("users", "roll_number")
