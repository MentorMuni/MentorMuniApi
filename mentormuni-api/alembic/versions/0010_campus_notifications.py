"""Campus notifications: kind / event_date / delivery_status + HODS audience.

Revision ID: 0010_campus_notifications
Revises: 0009_org_admin_title
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_campus_notifications"
down_revision: Union[str, None] = "0009_org_admin_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "kind",
            sa.String(length=32),
            nullable=False,
            server_default="announcement",
        ),
    )
    op.add_column(
        "notifications",
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "delivery_status",
            sa.String(length=32),
            nullable=False,
            server_default="queued",
        ),
    )


def downgrade() -> None:
    op.drop_column("notifications", "delivery_status")
    op.drop_column("notifications", "event_date")
    op.drop_column("notifications", "kind")
