"""Daily performance snapshots for readiness trends."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.database.base import Base


class OrgPerformanceSnapshot(Base):
    __tablename__ = "org_performance_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "department_id",
            "snapshot_date",
            name="uq_org_perf_snapshot_day",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 0 = campus-wide (organization scope)
    department_id: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    metrics_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
