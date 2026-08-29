"""Add organizations.portal_slug for college subdomains.

Revision ID: 0028_org_portal_slug
Revises: 0027_student_intelligence_uniques
"""

from __future__ import annotations

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028_org_portal_slug"
down_revision: Union[str, None] = "0027_student_intelligence_uniques"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RESERVED = {
    "www",
    "app",
    "api",
    "admin",
    "platform",
    "mail",
    "ftp",
    "staging",
    "cdn",
    "static",
    "assets",
    "mentormuni",
    "public",
    "individual",
    "student",
    "students",
    "org",
    "organization",
    "tpo",
    "hod",
    "help",
    "status",
    "docs",
}


def _normalize(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("portal_slug", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_organizations_portal_slug",
        "organizations",
        ["portal_slug"],
        unique=True,
    )

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, code, organization_type FROM organizations ORDER BY id ASC"
        )
    ).fetchall()
    used: set[str] = set()
    for row in rows:
        org_id, code, org_type = row[0], row[1], row[2]
        if str(org_type).upper() == "PUBLIC":
            continue
        base = _normalize(str(code or ""))
        if len(base) < 3:
            base = f"org-{org_id}"
        if base in RESERVED:
            base = f"{base}-campus"
        slug = base
        n = 2
        while slug in used or slug in RESERVED:
            slug = f"{base}-{n}"
            n += 1
            if len(slug) > 32:
                slug = f"org-{org_id}"
                break
        used.add(slug)
        conn.execute(
            sa.text("UPDATE organizations SET portal_slug = :slug WHERE id = :id"),
            {"slug": slug, "id": org_id},
        )


def downgrade() -> None:
    op.drop_index("ix_organizations_portal_slug", table_name="organizations")
    op.drop_column("organizations", "portal_slug")
