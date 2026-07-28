"""
Table 2: subscription_plans  (master catalog)

Examples:
  - Enterprise (COLLEGE, 1500 students, 12 months)
  - Premium Student (INDIVIDUAL, 1 student, 6 months)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base
from app.models.enums import PlanStatus, PlanType

if TYPE_CHECKING:
    from app.models.organization_subscription import OrganizationSubscription


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    plan_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    plan_type: Mapped[str] = mapped_column(String(32), nullable=False)  # COLLEGE | INDIVIDUAL

    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    max_students: Mapped[int] = mapped_column(Integer, nullable=False)
    # Numeric keeps money precise (never use float for currency).
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PlanStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization_subscriptions: Mapped[list["OrganizationSubscription"]] = relationship(
        back_populates="plan",
    )

    def __repr__(self) -> str:
        return f"<SubscriptionPlan id={self.id} name={self.plan_name!r} type={self.plan_type}>"
