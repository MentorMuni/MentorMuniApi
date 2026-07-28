"""phase1_core_tables

Revision ID: 0001_phase1_core
Revises:
Create Date: 2026-07-28

Creates the 7 Phase 1 tables and seeds:
  - roles (ORG_ADMIN, DEPARTMENT_ADMIN, STUDENT)
  - MentorMuni Public organization (for all B2C students)
  - starter subscription plans (Enterprise, Premium Student)
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_phase1_core"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. organizations
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("organization_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=32), nullable=True),
        sa.Column("address", sa.String(length=512), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=128), nullable=True),
        sa.Column("country", sa.String(length=128), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_organizations_code", "organizations", ["code"], unique=False)

    # ------------------------------------------------------------------
    # 2. subscription_plans
    # ------------------------------------------------------------------
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("plan_name", sa.String(length=128), nullable=False),
        sa.Column("plan_type", sa.String(length=32), nullable=False),
        sa.Column("duration_months", sa.Integer(), nullable=False),
        sa.Column("max_students", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_name"),
    )

    # ------------------------------------------------------------------
    # 3. organization_subscriptions
    # ------------------------------------------------------------------
    op.create_table(
        "organization_subscriptions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("student_limit", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_organization_subscriptions_organization_id",
        "organization_subscriptions",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_subscriptions_plan_id",
        "organization_subscriptions",
        ["plan_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 4. roles
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("role_code", sa.String(length=64), nullable=False),
        sa.Column("role_name", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_code"),
    )
    op.create_index("ix_roles_role_code", "roles", ["role_code"], unique=False)

    # ------------------------------------------------------------------
    # 5. departments
    # ------------------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_departments_org_code"),
    )
    op.create_index(
        "ix_departments_organization_id",
        "departments",
        ["organization_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 6. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("department_id", sa.BigInteger(), nullable=True),
        sa.Column("role_id", sa.BigInteger(), nullable=False),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("mobile", sa.String(length=32), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("approved_by", sa.BigInteger(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_users_org_email"),
        sa.UniqueConstraint("organization_id", "username", name="uq_users_org_username"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"], unique=False)
    op.create_index("ix_users_department_id", "users", ["department_id"], unique=False)
    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_status", "users", ["status"], unique=False)

    # ------------------------------------------------------------------
    # 7. organization_features
    # ------------------------------------------------------------------
    op.create_table(
        "organization_features",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("feature_code", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("configuration_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "feature_code",
            name="uq_org_features_org_code",
        ),
    )
    op.create_index(
        "ix_organization_features_organization_id",
        "organization_features",
        ["organization_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # Seed data (idempotent-ish: only runs on fresh upgrade)
    # ------------------------------------------------------------------
    op.execute(
        """
        INSERT INTO roles (role_code, role_name) VALUES
            ('ORG_ADMIN', 'Organization Admin (TPO)'),
            ('DEPARTMENT_ADMIN', 'Department Admin (HOD)'),
            ('STUDENT', 'Student')
        """
    )

    op.execute(
        """
        INSERT INTO organizations (
            name, code, organization_type, status, country
        ) VALUES (
            'MentorMuni Public',
            'PUBLIC',
            'PUBLIC',
            'ACTIVE',
            'India'
        )
        """
    )

    op.execute(
        """
        INSERT INTO subscription_plans (
            plan_name, plan_type, duration_months, max_students, price, status
        ) VALUES
            ('Enterprise', 'COLLEGE', 12, 1500, 0.00, 'ACTIVE'),
            ('Premium Student', 'INDIVIDUAL', 6, 1, 0.00, 'ACTIVE')
        """
    )


def downgrade() -> None:
    op.drop_index("ix_organization_features_organization_id", table_name="organization_features")
    op.drop_table("organization_features")

    op.drop_index("ix_users_status", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_department_id", table_name="users")
    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_departments_organization_id", table_name="departments")
    op.drop_table("departments")

    op.drop_index("ix_roles_role_code", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_organization_subscriptions_plan_id", table_name="organization_subscriptions")
    op.drop_index(
        "ix_organization_subscriptions_organization_id",
        table_name="organization_subscriptions",
    )
    op.drop_table("organization_subscriptions")

    op.drop_table("subscription_plans")

    op.drop_index("ix_organizations_code", table_name="organizations")
    op.drop_table("organizations")
