"""Store college logos in Postgres (BYTEA).

Revision ID: 0029_org_logo
Revises: 0028_org_portal_slug
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_org_logo"
down_revision: Union[str, None] = "0028_org_portal_slug"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("logo_bytes", sa.LargeBinary(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("logo_content_type", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("logo_updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "logo_updated_at")
    op.drop_column("organizations", "logo_content_type")
    op.drop_column("organizations", "logo_bytes")
