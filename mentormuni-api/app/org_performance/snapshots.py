"""Record and query daily performance snapshots for trend charts."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.org_performance.models import OrgPerformanceSnapshot
from app.org_performance.schemas import PerformanceSummaryOut, PerformanceTrendPoint, PerformanceTrendsOut


def _dept_key(department_id: Optional[int]) -> int:
    return int(department_id or 0)


def _metrics_from_summary(summary: PerformanceSummaryOut) -> dict:
    return {
        "students_total": summary.students_total,
        "students_scored": summary.students_scored,
        "coverage_pct": summary.coverage_pct,
        "avg_readiness": summary.avg_readiness,
        "drive_ready_pct": summary.drive_ready_pct,
        "drive_ready_of_scored_pct": summary.drive_ready_of_scored_pct,
        "bands": summary.bands.model_dump(),
        "pillars": summary.pillars.model_dump(),
        "active_7d": summary.active_7d,
        "inactive_14d": summary.inactive_14d,
        "never_started": summary.never_started,
    }


async def record_snapshot(
    db: AsyncSession,
    *,
    organization_id: int,
    department_id: Optional[int],
    summary: PerformanceSummaryOut,
) -> None:
    dept_key = _dept_key(department_id)
    today = date.today()
    metrics = _metrics_from_summary(summary)
    stmt = (
        insert(OrgPerformanceSnapshot)
        .values(
            organization_id=organization_id,
            department_id=dept_key,
            snapshot_date=today,
            metrics_json=metrics,
        )
        .on_conflict_do_update(
            constraint="uq_org_perf_snapshot_day",
            set_={"metrics_json": metrics},
        )
    )
    await db.execute(stmt)
    await db.commit()


async def get_performance_trends(
    db: AsyncSession,
    *,
    organization_id: int,
    department_id: Optional[int],
    days: int = 30,
) -> PerformanceTrendsOut:
    dept_key = _dept_key(department_id)
    since = date.today() - timedelta(days=max(1, min(days, 90)))
    rows = (
        await db.execute(
            select(OrgPerformanceSnapshot)
            .where(OrgPerformanceSnapshot.organization_id == organization_id)
            .where(OrgPerformanceSnapshot.department_id == dept_key)
            .where(OrgPerformanceSnapshot.snapshot_date >= since)
            .order_by(OrgPerformanceSnapshot.snapshot_date.asc())
        )
    ).scalars().all()

    points = [
        PerformanceTrendPoint(
            date=row.snapshot_date.isoformat(),
            avg_readiness=(row.metrics_json or {}).get("avg_readiness"),
            coverage_pct=(row.metrics_json or {}).get("coverage_pct"),
            drive_ready_of_scored_pct=(row.metrics_json or {}).get("drive_ready_of_scored_pct"),
            students_scored=(row.metrics_json or {}).get("students_scored"),
        )
        for row in rows
    ]
    return PerformanceTrendsOut(
        organization_id=organization_id,
        department_id=department_id,
        days=days,
        points=points,
    )
