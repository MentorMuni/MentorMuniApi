"""Platform user must_change_password flag.

Revision ID: 0006_plat_must_chg_pwd
Revises: 0005_student_enrollment
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_plat_must_chg_pwd"
down_revision: Union[str, None] = "0005_student_enrollment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alembic default version_num is VARCHAR(32); widen for longer revision ids.
    op.execute(
        "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"
    )
    op.add_column(
        "platform_users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("platform_users", "must_change_password")
