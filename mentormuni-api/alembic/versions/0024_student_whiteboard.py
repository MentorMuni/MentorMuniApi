"""Student White Board sticky notes and daily mentorship.

Revision ID: 0024_student_whiteboard
Revises: 0023_fear_factor_plan_actions
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_student_whiteboard"
down_revision: Union[str, None] = "0023_fear_factor_plan_actions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "whiteboard_notes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("board_date", sa.Date(), nullable=False),
        sa.Column("pin_x", sa.Float(), nullable=False),
        sa.Column("pin_y", sa.Float(), nullable=False),
        sa.Column("rotation", sa.Float(), nullable=False),
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
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whiteboard_notes_student_id", "whiteboard_notes", ["student_id"])
    op.create_index("ix_whiteboard_notes_organization_id", "whiteboard_notes", ["organization_id"])
    op.create_index("ix_whiteboard_notes_status", "whiteboard_notes", ["status"])
    op.create_index("ix_whiteboard_notes_board_date", "whiteboard_notes", ["board_date"])
    op.create_index(
        "ix_whiteboard_notes_student_status",
        "whiteboard_notes",
        ["student_id", "status"],
    )
    op.create_index(
        "ix_whiteboard_notes_student_board_date",
        "whiteboard_notes",
        ["student_id", "board_date"],
    )

    op.create_table(
        "whiteboard_mentorships",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("mentorship_date", sa.Date(), nullable=False),
        sa.Column("source_notes_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("greeting", sa.Text(), nullable=False),
        sa.Column("what_changed", sa.Text(), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=False),
        sa.Column(
            "actions_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("callout", sa.Text(), nullable=False),
        sa.Column("closing", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.ForeignKeyConstraint(["student_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "mentorship_date", name="uq_whiteboard_mentorship_student_date"),
    )
    op.create_index("ix_whiteboard_mentorships_student_id", "whiteboard_mentorships", ["student_id"])
    op.create_index(
        "ix_whiteboard_mentorships_organization_id",
        "whiteboard_mentorships",
        ["organization_id"],
    )
    op.create_index("ix_whiteboard_mentorships_status", "whiteboard_mentorships", ["status"])


def downgrade() -> None:
    op.drop_index("ix_whiteboard_mentorships_status", table_name="whiteboard_mentorships")
    op.drop_index("ix_whiteboard_mentorships_organization_id", table_name="whiteboard_mentorships")
    op.drop_index("ix_whiteboard_mentorships_student_id", table_name="whiteboard_mentorships")
    op.drop_table("whiteboard_mentorships")
    op.drop_index("ix_whiteboard_notes_student_board_date", table_name="whiteboard_notes")
    op.drop_index("ix_whiteboard_notes_student_status", table_name="whiteboard_notes")
    op.drop_index("ix_whiteboard_notes_board_date", table_name="whiteboard_notes")
    op.drop_index("ix_whiteboard_notes_status", table_name="whiteboard_notes")
    op.drop_index("ix_whiteboard_notes_organization_id", table_name="whiteboard_notes")
    op.drop_index("ix_whiteboard_notes_student_id", table_name="whiteboard_notes")
    op.drop_table("whiteboard_notes")
