"""Alembic: company_intelligence cache table.

Revision ID: 0016_company_intelligence
Revises: 0015_dept_admin_title
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_company_intelligence"
down_revision: Union[str, None] = "0015_dept_admin_title"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "company_intelligence",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("company_name", sa.String(length=160), nullable=False),
        sa.Column("role_name", sa.String(length=160), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("company_key", sa.String(length=160), nullable=False),
        sa.Column("role_key", sa.String(length=160), nullable=False),
        sa.Column("country_key", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="generating"),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("evidence_strength", sa.String(length=32), nullable=True),
        sa.Column("last_updated_estimate", sa.String(length=8), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "prompt_version",
            sa.String(length=64),
            nullable=False,
            server_default="company_intelligence_v1",
        ),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_company_intelligence_slug"),
        sa.UniqueConstraint(
            "company_key",
            "role_key",
            "country_key",
            name="uq_company_intelligence_keys",
        ),
    )
    op.create_index("ix_company_intelligence_slug", "company_intelligence", ["slug"])
    op.create_index("ix_company_intelligence_company_key", "company_intelligence", ["company_key"])
    op.create_index("ix_company_intelligence_status", "company_intelligence", ["status"])


def downgrade() -> None:
    op.drop_index("ix_company_intelligence_status", table_name="company_intelligence")
    op.drop_index("ix_company_intelligence_company_key", table_name="company_intelligence")
    op.drop_index("ix_company_intelligence_slug", table_name="company_intelligence")
    op.drop_table("company_intelligence")
