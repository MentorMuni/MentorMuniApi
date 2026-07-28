"""
organization_subscriptions (API name: subscriptions)

Platform assigns plan + student limit + validity.
used_students is incremented when students register (enforced later).
plan_name is a snapshot so historical rows stay readable if the catalog changes.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.database.base import Base
from app.models.enums import SubscriptionStatus

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.subscription_plan import SubscriptionPlan


class OrganizationSubscription(Base):
    __tablename__ = "organization_subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    organization_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Snapshot of plan.plan_name at assignment time (matches Platform UI field).
    plan_name: Mapped[str] = mapped_column(String(128), nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    student_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    used_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SubscriptionStatus.ACTIVE.value,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(back_populates="subscriptions")
    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="organization_subscriptions")

    def __repr__(self) -> str:
        return (
            f"<OrganizationSubscription id={self.id} "
            f"org={self.organization_id} plan={self.plan_name!r} status={self.status}>"
        )
