"""platform_portal

Revision ID: 0002_platform_portal
Revises: 0001_phase1_core
Create Date: 2026-07-28

Platform Admin portal support:
  - feature_catalog + organization_features.feature_id
  - organization_subscriptions.plan_name + used_students
  - users activation token fields
  - platform_users (+ seed admin)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_platform_portal"
down_revision: Union[str, None] = "0001_phase1_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # feature_catalog
    # ------------------------------------------------------------------
    op.create_table(
        "feature_catalog",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("feature_code", sa.String(length=64), nullable=False),
        sa.Column("feature_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_code"),
    )
    op.create_index("ix_feature_catalog_feature_code", "feature_catalog", ["feature_code"])

    op.execute(
        """
        INSERT INTO feature_catalog (feature_code, feature_name, category, description, status)
        VALUES
            ('resume_ats', 'Resume ATS', 'Career', 'Resume ATS scoring', 'ACTIVE'),
            ('skill_readiness', 'Skill Readiness', 'Readiness', 'Skill readiness plans', 'ACTIVE'),
            ('aptitude_readiness', 'Aptitude Readiness', 'Readiness', 'Aptitude readiness plans', 'ACTIVE'),
            ('ai_mentor', 'AI Mentor', 'AI', 'AI mentoring chat', 'ACTIVE'),
            ('ai_mock', 'AI Mock Interview', 'AI', 'AI mock interview', 'ACTIVE'),
            ('coding', 'Coding Round', 'Assessment', 'Coding assessments', 'ACTIVE'),
            ('industry_interview', 'Industry Interview', 'AI', 'Industry interview practice', 'ACTIVE'),
            ('assignments', 'Assignments', 'Learning', 'Assignments module', 'ACTIVE'),
            ('competitions', 'Competitions', 'Learning', 'Competitions module', 'ACTIVE')
        """
    )

    # ------------------------------------------------------------------
    # organization_features: feature_code → feature_id
    # ------------------------------------------------------------------
    op.add_column(
        "organization_features",
        sa.Column("feature_id", sa.BigInteger(), nullable=True),
    )

    # Backfill any existing rows that used feature_code (table may be empty).
    op.execute(
        """
        UPDATE organization_features ofeat
        SET feature_id = fc.id
        FROM feature_catalog fc
        WHERE ofeat.feature_code = fc.feature_code
        """
    )

    op.drop_constraint("uq_org_features_org_code", "organization_features", type_="unique")
    op.drop_column("organization_features", "feature_code")

    # Delete orphan rows that could not be mapped (should be none).
    op.execute("DELETE FROM organization_features WHERE feature_id IS NULL")

    op.alter_column("organization_features", "feature_id", nullable=False)
    op.create_foreign_key(
        "fk_org_features_feature_id",
        "organization_features",
        "feature_catalog",
        ["feature_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_organization_features_feature_id",
        "organization_features",
        ["feature_id"],
    )
    op.create_unique_constraint(
        "uq_org_features_org_feature",
        "organization_features",
        ["organization_id", "feature_id"],
    )

    # ------------------------------------------------------------------
    # organization_subscriptions: plan_name + used_students
    # ------------------------------------------------------------------
    op.add_column(
        "organization_subscriptions",
        sa.Column("plan_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "organization_subscriptions",
        sa.Column("used_students", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        UPDATE organization_subscriptions os
        SET plan_name = sp.plan_name
        FROM subscription_plans sp
        WHERE os.plan_id = sp.id
        """
    )
    op.alter_column("organization_subscriptions", "plan_name", nullable=False)
    op.alter_column("organization_subscriptions", "used_students", server_default=None)

    # ------------------------------------------------------------------
    # users: activation token for TPO invite flow
    # ------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("activation_token_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("activation_expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ------------------------------------------------------------------
    # platform_users
    # ------------------------------------------------------------------
    op.create_table(
        "platform_users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_platform_users_email", "platform_users", ["email"])

    # Seed default platform admin. Password: ChangeMe123!  (change after first login)
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    admin_hash = pwd.hash("ChangeMe123!")
    op.execute(
        sa.text(
            """
            INSERT INTO platform_users (name, email, password_hash, role, status)
            VALUES (:name, :email, :password_hash, :role, :status)
            """
        ).bindparams(
            name="Platform Admin",
            email="admin@mentormuni.com",
            password_hash=admin_hash,
            role="PLATFORM_ADMIN",
            status="ACTIVE",
        )
    )


def downgrade() -> None:
    op.drop_index("ix_platform_users_email", table_name="platform_users")
    op.drop_table("platform_users")

    op.drop_column("users", "activation_expires_at")
    op.drop_column("users", "activation_token_hash")

    op.drop_column("organization_subscriptions", "used_students")
    op.drop_column("organization_subscriptions", "plan_name")

    op.drop_constraint("uq_org_features_org_feature", "organization_features", type_="unique")
    op.drop_index("ix_organization_features_feature_id", table_name="organization_features")
    op.drop_constraint("fk_org_features_feature_id", "organization_features", type_="foreignkey")

    op.add_column(
        "organization_features",
        sa.Column("feature_code", sa.String(length=64), nullable=True),
    )
    op.execute(
        """
        UPDATE organization_features ofeat
        SET feature_code = fc.feature_code
        FROM feature_catalog fc
        WHERE ofeat.feature_id = fc.id
        """
    )
    op.alter_column("organization_features", "feature_code", nullable=False)
    op.drop_column("organization_features", "feature_id")
    op.create_unique_constraint(
        "uq_org_features_org_code",
        "organization_features",
        ["organization_id", "feature_code"],
    )

    op.drop_index("ix_feature_catalog_feature_code", table_name="feature_catalog")
    op.drop_table("feature_catalog")
