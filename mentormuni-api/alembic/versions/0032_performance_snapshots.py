"""Daily performance snapshot table for readiness trends.

Revision ID: 0032_performance_snapshots
Revises: 0031_baseline_sprint_start
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032_performance_snapshots"
down_revision: Union[str, None] = "0031_baseline_sprint_start"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_performance_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("department_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column(
            "metrics_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "department_id",
            "snapshot_date",
            name="uq_org_perf_snapshot_day",
        ),
    )
    op.create_index(
        "ix_org_perf_snapshots_org_dept_date",
        "org_performance_snapshots",
        ["organization_id", "department_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_org_perf_snapshots_org_dept_date", table_name="org_performance_snapshots")
    op.drop_table("org_performance_snapshots")
