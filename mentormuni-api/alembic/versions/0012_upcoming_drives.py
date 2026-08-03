"""Upcoming placement drives for Org Admins (TPO/Dean/Director).

Revision ID: 0012_upcoming_drives
Revises: 0011_workspace_items
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_upcoming_drives"
down_revision: Union[str, None] = "0011_workspace_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "upcoming_drives",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("eligibility_criteria", sa.Text(), nullable=False),
        sa.Column("drive_date", sa.Date(), nullable=False),
        sa.Column("remark", sa.Text(), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_upcoming_drives_organization_id", "upcoming_drives", ["organization_id"])
    op.create_index("ix_upcoming_drives_drive_date", "upcoming_drives", ["drive_date"])


def downgrade() -> None:
    op.drop_index("ix_upcoming_drives_drive_date", table_name="upcoming_drives")
    op.drop_index("ix_upcoming_drives_organization_id", table_name="upcoming_drives")
    op.drop_table("upcoming_drives")
