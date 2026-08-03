"""Personal workspace items for Org Admins.

Revision ID: 0011_workspace_items
Revises: 0010_campus_notifications
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_workspace_items"
down_revision: Union[str, None] = "0010_campus_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="todo"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspace_items_user_id", "workspace_items", ["user_id"])
    op.create_index("ix_workspace_items_organization_id", "workspace_items", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_items_organization_id", table_name="workspace_items")
    op.drop_index("ix_workspace_items_user_id", table_name="workspace_items")
    op.drop_table("workspace_items")
