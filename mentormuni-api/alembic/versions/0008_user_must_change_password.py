"""Org users must_change_password for forced password change.

Revision ID: 0008_user_must_change_password
Revises: 0007_subscription_plan_codes
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_user_must_change_password"
down_revision: Union[str, None] = "0007_subscription_plan_codes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
