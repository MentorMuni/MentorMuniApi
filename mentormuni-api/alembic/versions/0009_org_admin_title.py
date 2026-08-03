"""ORG_ADMIN titles: TPO / DEAN / DIRECTOR (same access).

Revision ID: 0009_org_admin_title
Revises: 0008_user_must_change_password
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_org_admin_title"
down_revision: Union[str, None] = "0008_user_must_change_password"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("org_admin_title", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_users_org_admin_title", "users", ["org_admin_title"])

    # Existing college admins become primary TPO.
    op.execute(
        """
        UPDATE users AS u
        SET org_admin_title = 'TPO'
        FROM roles AS r
        WHERE u.role_id = r.id
          AND r.role_code = 'ORG_ADMIN'
          AND u.org_admin_title IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_users_org_admin_title", table_name="users")
    op.drop_column("users", "org_admin_title")
