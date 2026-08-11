"""Help Center tickets for student/org reporters and MentorMuni Support Inbox.

Revision ID: 0022_platform_support_tickets
Revises: 0021_private_intervention_tables
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_platform_support_tickets"
down_revision: Union[str, None] = "0021_private_intervention_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "platform_support_tickets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_name", sa.String(length=255), nullable=False),
        sa.Column("organization_code", sa.String(length=64), nullable=False),
        sa.Column("source_portal", sa.String(length=32), nullable=False),
        sa.Column("reporter_user_id", sa.BigInteger(), nullable=False),
        sa.Column("reporter_role_code", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="OPEN"),
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
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by_kind", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pst_reporter_created", "platform_support_tickets", ["reporter_user_id", "created_at"])
    op.create_index("ix_pst_status_updated", "platform_support_tickets", ["status", "updated_at"])
    op.create_index("ix_pst_organization_id", "platform_support_tickets", ["organization_id"])
    op.create_index("ix_pst_source_portal", "platform_support_tickets", ["source_portal"])

    op.create_table(
        "platform_support_replies",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticket_id", sa.BigInteger(), nullable=False),
        sa.Column("author_kind", sa.String(length=16), nullable=False),
        sa.Column("author_user_id", sa.BigInteger(), nullable=True),
        sa.Column("author_platform_user_id", sa.BigInteger(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("attachments_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["platform_support_tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["author_platform_user_id"], ["platform_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_psr_ticket_id", "platform_support_replies", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_psr_ticket_id", table_name="platform_support_replies")
    op.drop_table("platform_support_replies")
    op.drop_index("ix_pst_source_portal", table_name="platform_support_tickets")
    op.drop_index("ix_pst_organization_id", table_name="platform_support_tickets")
    op.drop_index("ix_pst_status_updated", table_name="platform_support_tickets")
    op.drop_index("ix_pst_reporter_created", table_name="platform_support_tickets")
    op.drop_table("platform_support_tickets")
