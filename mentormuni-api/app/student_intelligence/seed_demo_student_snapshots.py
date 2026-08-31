"""Seed demo daily readiness snapshots for a student (trend chart demos).

Usage (from mentormuni-api/):
  python -m app.student_intelligence.seed_demo_student_snapshots --email student@college.edu
  python -m app.student_intelligence.seed_demo_student_snapshots --student-id 42
  python -m app.student_intelligence.seed_demo_student_snapshots --cleanup --student-id 42
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.user import User
from app.student_intelligence.models import StudentReadinessSnapshot
from app.student_intelligence.readiness import PILLAR_LABELS, PILLARS

DEMO_SEED_KEY = "demo_seed"


def _async_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _day_metrics(day_index: int, total_days: int, base: int) -> dict:
    progress = day_index / max(1, total_days - 1)
    wave = math.sin(day_index / 4.0) * 1.5
    overall = int(round(base + progress * 16 + wave + random.uniform(-2, 2)))
    overall = max(0, min(100, overall))
    measured = min(6, 2 + int(progress * 4))
    pillars = {}
    for i, key in enumerate(PILLARS):
        has = i < measured
        score = int(round(overall - 8 + i * 2 + random.uniform(-3, 3))) if has else 0
        pillars[key] = {
            "label": PILLAR_LABELS[key],
            "score": max(0, min(100, score)) if has else 0,
            "hasData": has,
            "attempts": 1 + (1 if has and i % 2 == 0 else 0),
            "confidence": 0.5 if has else 0,
            "trend": random.choice([-2, 0, 1, 3]) if has else None,
            "last_at": None,
            "weight": 0.15,
        }
    pillars["_demo_seed"] = True
    weakest = PILLARS[measured - 1] if measured else PILLARS[0]
    return {
        "overall": overall,
        "base": overall,
        "execution_multiplier": Decimal("1.0"),
        "coverage": Decimal(str(round(measured / 6, 4))),
        "measured_pillars": measured,
        "total_pillars": 6,
        "eta_days": max(0, 85 - overall),
        "pillars": pillars,
        "focus_pillar": weakest,
        "weakest_pillar": weakest,
        "gates": [],
    }


async def seed(db, student_id: int, days: int = 30) -> int:
    total = max(2, min(days, 90))
    today = date.today()
    start = today - timedelta(days=total - 1)
    random.seed(student_id)
    count = 0
    for i in range(total):
        snap_date = start + timedelta(days=i)
        m = _day_metrics(i, total, base=48)
        stmt = (
            insert(StudentReadinessSnapshot)
            .values(
                student_id=student_id,
                snapshot_date=snap_date,
                overall=m["overall"],
                base=m["base"],
                execution_multiplier=m["execution_multiplier"],
                coverage=m["coverage"],
                measured_pillars=m["measured_pillars"],
                total_pillars=m["total_pillars"],
                eta_days=m["eta_days"],
                pillars=m["pillars"],
                focus_pillar=m["focus_pillar"],
                weakest_pillar=m["weakest_pillar"],
                gates=m["gates"],
            )
            .on_conflict_do_update(
                constraint="uq_student_readiness_snapshot_day",
                set_={
                    "overall": m["overall"],
                    "base": m["base"],
                    "coverage": m["coverage"],
                    "measured_pillars": m["measured_pillars"],
                    "pillars": m["pillars"],
                    "focus_pillar": m["focus_pillar"],
                    "weakest_pillar": m["weakest_pillar"],
                },
            )
        )
        await db.execute(stmt)
        count += 1
    await db.commit()
    return count


async def cleanup(db, student_id: int) -> int:
    result = await db.execute(
        delete(StudentReadinessSnapshot).where(
            StudentReadinessSnapshot.student_id == student_id,
            StudentReadinessSnapshot.pillars.contains({"_demo_seed": True}),
        )
    )
    await db.commit()
    return int(result.rowcount or 0)


async def _resolve_student_id(db, *, email: str | None, student_id: int | None) -> int:
    if student_id is not None:
        return student_id
    if not email:
        raise SystemExit("Provide --student-id or --email")
    row = (await db.execute(select(User.id).where(User.email == email.lower()))).scalar_one_or_none()
    if row is None:
        raise SystemExit(f"No user found for email: {email}")
    return int(row)


async def main_async(args: argparse.Namespace) -> None:
    if not settings.is_database_configured:
        raise SystemExit("DATABASE_URL is not configured.")
    engine = create_async_engine(_async_db_url(settings.database_url), pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as db:
            sid = await _resolve_student_id(db, email=args.email, student_id=args.student_id)
            if args.cleanup:
                n = await cleanup(db, sid)
                print(f"Removed {n} demo student snapshot(s) for student_id={sid}.")
                return
            n = await seed(db, sid, days=args.days)
            print(f"Seeded {n} demo snapshot(s) for student_id={sid}.")
            print("Remove later with --cleanup")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email")
    parser.add_argument("--student-id", type=int)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--cleanup", action="store_true")
    asyncio.run(main_async(parser.parse_args()))


if __name__ == "__main__":
    main()
