"""Seed demo performance snapshots for trend-chart demos.

Usage (from mentormuni-api/):
  python -m app.org_performance.seed_demo_snapshots
  python -m app.org_performance.seed_demo_snapshots --org-id 1
  python -m app.org_performance.seed_demo_snapshots --cleanup

Rows are tagged with metrics_json.demo_seed=true so they can be removed later
without touching real snapshots recorded by the app.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
from datetime import date, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.department import Department
from app.models.organization import Organization
from app.org_performance.models import OrgPerformanceSnapshot

DEMO_SEED_KEY = "demo_seed"


def _async_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _demo_metrics(
    *,
    day_index: int,
    total_days: int,
    base_readiness: float,
    base_coverage: float,
    base_drive_ready: float,
    students_total: int,
) -> dict:
    """Build one day's metrics with a gentle upward trend + small noise."""
    progress = day_index / max(1, total_days - 1)
    wave = math.sin(day_index / 4.5) * 1.2
    readiness = round(base_readiness + progress * 14 + wave + random.uniform(-1.5, 1.5), 1)
    coverage = round(base_coverage + progress * 18 + wave * 0.8 + random.uniform(-2, 2), 1)
    drive_ready = round(
        base_drive_ready + progress * 12 + wave * 0.6 + random.uniform(-1.5, 1.5),
        1,
    )
    scored = max(1, int(students_total * (coverage / 100)))
    return {
        DEMO_SEED_KEY: True,
        "students_total": students_total,
        "students_scored": scored,
        "coverage_pct": min(100.0, max(0.0, coverage)),
        "avg_readiness": min(100.0, max(0.0, readiness)),
        "drive_ready_pct": min(100.0, max(0.0, drive_ready * 0.85)),
        "drive_ready_of_scored_pct": min(100.0, max(0.0, drive_ready)),
        "bands": {
            "excellent": max(0, int(scored * 0.08)),
            "good": max(0, int(scored * 0.22)),
            "fair": max(0, int(scored * 0.35)),
            "needs_work": max(0, int(scored * 0.35)),
        },
        "pillars": {
            "aptitude": round(readiness * 0.92, 1),
            "coding": round(readiness * 0.88, 1),
            "communication": round(readiness * 0.95, 1),
            "resume": round(readiness * 0.9, 1),
        },
        "active_7d": max(1, int(students_total * (0.45 + progress * 0.2))),
        "inactive_14d": max(0, int(students_total * (0.25 - progress * 0.08))),
        "never_started": max(0, students_total - scored),
    }


async def _upsert_demo_snapshot(
    db: AsyncSession,
    *,
    organization_id: int,
    department_id: int,
    snapshot_date: date,
    metrics: dict,
) -> None:
    stmt = (
        insert(OrgPerformanceSnapshot)
        .values(
            organization_id=organization_id,
            department_id=department_id,
            snapshot_date=snapshot_date,
            metrics_json=metrics,
        )
        .on_conflict_do_update(
            constraint="uq_org_perf_snapshot_day",
            set_={"metrics_json": metrics},
        )
    )
    await db.execute(stmt)


async def seed_demo_snapshots(
    db: AsyncSession,
    *,
    organization_id: int | None = None,
    days: int = 30,
) -> int:
    org_query = select(Organization.id)
    if organization_id is not None:
        org_query = org_query.where(Organization.id == organization_id)
    org_ids = list((await db.execute(org_query)).scalars().all())
    if not org_ids:
        raise SystemExit("No organizations found to seed.")

    total_days = max(2, min(days, 90))
    today = date.today()
    start = today - timedelta(days=total_days - 1)
    random.seed(42)
    inserted = 0

    for org_id in org_ids:
        dept_rows = (
            await db.execute(
                select(Department.id).where(Department.organization_id == org_id).order_by(Department.id)
            )
        ).scalars().all()
        scopes: list[tuple[int, float, float, float, int]] = [
            (0, 48.0, 38.0, 14.0, 240),
        ]
        offsets = [(-4, -6, -3), (2, 4, 2), (-2, 2, -1), (5, 8, 4), (-6, -4, -2)]
        for idx, dept_id in enumerate(dept_rows):
            off = offsets[idx % len(offsets)]
            scopes.append((int(dept_id), 48.0 + off[0], 38.0 + off[1], 14.0 + off[2], 60))

        for dept_key, base_r, base_c, base_d, students in scopes:
            for i in range(total_days):
                snap_date = start + timedelta(days=i)
                metrics = _demo_metrics(
                    day_index=i,
                    total_days=total_days,
                    base_readiness=base_r,
                    base_coverage=base_c,
                    base_drive_ready=base_d,
                    students_total=students,
                )
                await _upsert_demo_snapshot(
                    db,
                    organization_id=org_id,
                    department_id=dept_key,
                    snapshot_date=snap_date,
                    metrics=metrics,
                )
                inserted += 1

    await db.commit()
    return inserted


async def cleanup_demo_snapshots(
    db: AsyncSession,
    *,
    organization_id: int | None = None,
) -> int:
    stmt = delete(OrgPerformanceSnapshot).where(
        OrgPerformanceSnapshot.metrics_json.contains({DEMO_SEED_KEY: True})
    )
    if organization_id is not None:
        stmt = stmt.where(OrgPerformanceSnapshot.organization_id == organization_id)
    result = await db.execute(stmt)
    await db.commit()
    return int(result.rowcount or 0)


async def _main_async(args: argparse.Namespace) -> None:
    if not settings.is_database_configured:
        raise SystemExit("DATABASE_URL is not configured.")

    engine = create_async_engine(_async_db_url(settings.database_url), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as db:
            if args.cleanup:
                removed = await cleanup_demo_snapshots(db, organization_id=args.org_id)
                print(f"Removed {removed} demo snapshot row(s).")
                return

            count = await seed_demo_snapshots(
                db,
                organization_id=args.org_id,
                days=args.days,
            )
            print(
                f"Seeded {count} demo snapshot row(s) "
                f"({args.days} days, tagged demo_seed=true)."
            )
            print("Remove later with: python -m app.org_performance.seed_demo_snapshots --cleanup")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed or remove demo performance snapshots.")
    parser.add_argument("--org-id", type=int, default=None, help="Limit to one organization.")
    parser.add_argument("--days", type=int, default=30, help="Number of days to backfill (7–90).")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete rows tagged with demo_seed=true.",
    )
    args = parser.parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()
