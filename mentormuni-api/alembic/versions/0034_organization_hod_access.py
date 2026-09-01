"""Per-organization HOD access policy for TPO portal."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0034_organization_hod_access"
down_revision: Union[str, None] = "0033_hod_send_notification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_hod_access",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("can_invite_students", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("can_view_all_scores", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("can_assign_programs", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("can_notify_department", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("can_run_mocks", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", name="uq_organization_hod_access_org"),
    )
    op.create_index(
        "ix_organization_hod_access_organization_id",
        "organization_hod_access",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_organization_hod_access_organization_id", table_name="organization_hod_access")
    op.drop_table("organization_hod_access")
