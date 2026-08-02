"""Canonical subscription plan codes + COLLEGE catalog rows.

Revision ID: 0007_subscription_plan_codes
Revises: 0006_plat_must_chg_pwd
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_subscription_plan_codes"
down_revision: Union[str, None] = "0006_plat_must_chg_pwd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "subscription_plans",
        sa.Column("plan_code", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_subscription_plans_plan_code",
        "subscription_plans",
        ["plan_code"],
        unique=True,
    )

    # Backfill known rows by plan_name.
    op.execute(
        """
        UPDATE subscription_plans SET plan_code = 'ENTERPRISE'
        WHERE plan_name = 'Enterprise' AND plan_code IS NULL
        """
    )
    op.execute(
        """
        UPDATE subscription_plans SET plan_code = 'PREMIUM_STUDENT'
        WHERE plan_name = 'Premium Student' AND plan_code IS NULL
        """
    )

    # Canonical COLLEGE catalog (idempotent by plan_code / plan_name).
    op.execute(
        """
        INSERT INTO subscription_plans (
            plan_code, plan_name, plan_type, duration_months, max_students, price, status
        )
        SELECT 'STARTER', 'Starter', 'COLLEGE', 12, 200, 0.00, 'ACTIVE'
        WHERE NOT EXISTS (
            SELECT 1 FROM subscription_plans
            WHERE plan_code = 'STARTER' OR plan_name = 'Starter'
        )
        """
    )
    op.execute(
        """
        INSERT INTO subscription_plans (
            plan_code, plan_name, plan_type, duration_months, max_students, price, status
        )
        SELECT 'GROWTH', 'Growth', 'COLLEGE', 12, 800, 0.00, 'ACTIVE'
        WHERE NOT EXISTS (
            SELECT 1 FROM subscription_plans
            WHERE plan_code = 'GROWTH' OR plan_name = 'Growth'
        )
        """
    )
    op.execute(
        """
        INSERT INTO subscription_plans (
            plan_code, plan_name, plan_type, duration_months, max_students, price, status
        )
        SELECT 'ENTERPRISE', 'Enterprise', 'COLLEGE', 12, 1500, 0.00, 'ACTIVE'
        WHERE NOT EXISTS (
            SELECT 1 FROM subscription_plans
            WHERE plan_code = 'ENTERPRISE' OR plan_name = 'Enterprise'
        )
        """
    )
    op.execute(
        """
        UPDATE subscription_plans SET plan_code = 'STARTER'
        WHERE plan_name = 'Starter' AND plan_code IS NULL
        """
    )
    op.execute(
        """
        UPDATE subscription_plans SET plan_code = 'GROWTH'
        WHERE plan_name = 'Growth' AND plan_code IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_subscription_plans_plan_code", table_name="subscription_plans")
    op.drop_column("subscription_plans", "plan_code")
