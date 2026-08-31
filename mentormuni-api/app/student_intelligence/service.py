"""Student Intelligence P0 service — readiness, mastery, coverage, daily, targets."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from urllib.parse import quote

from app.models.user import User
from app.student_intelligence.mastery import (
    TOOL_MODALITY,
    apply_mastery_to_row,
    init_topic_mastery,
    row_to_mastery,
    schedule_next_review,
    update_mastery,
)
from app.student_intelligence.models import (
    StudentAttempt,
    StudentCoverageLedger,
    StudentDailyActivity,
    StudentDailyTaskLedger,
    StudentMemoryFact,
    StudentMissionAnchor,
    StudentReadinessSnapshot,
    StudentTarget,
    StudentTopicMastery,
)
from app.student_intelligence.plan_mission import build_day_index, infer_tool_code, tasks_for_plan_day
from app.student_intelligence.readiness import DEFAULT_TARGET, TOOL_PILLARS, compute_readiness
from app.student_intelligence.slate import ledger_from_rows, select_slate
from app.student_intelligence.syllabus import get_all_topics, prune_syllabus_for_companies
from app.student_roadmap.constants import (
    PLAN_STATUS_READY,
    STEP_STATUS_CURRENT,
    TOOL_META,
    WEEK1_NUMBER,
    WEEK_STATUS_DONE,
)
from app.student_roadmap.models import (
    StudentGeneratedRoadmap,
    StudentRoadmapStep,
    StudentRoadmapWeek,
)

from app.student_roadmap.plan_horizon import PLAN_HORIZON_MAX, plan_horizon_from_plan_json

CAMPUS_TZ = ZoneInfo("Asia/Kolkata")
PLAN_HORIZON_DAYS = PLAN_HORIZON_MAX  # legacy alias — actual length comes from generated plan
logger = logging.getLogger(__name__)


def _parse_date(value: str | date | None, fallback: date | None = None) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if value:
        return date.fromisoformat(str(value)[:10])
    if fallback:
        return fallback
    return datetime.now(CAMPUS_TZ).date()


def _campus_today() -> date:
    return datetime.now(CAMPUS_TZ).date()


def _plan_id_match(column, plan_id: int | None):
    if plan_id is None:
        return column.is_(None)
    return column == plan_id


async def _resolve_ledger_plan_id(
    db: AsyncSession,
    user: User,
    today: date,
    task_key: str,
    plan_id: int | None,
) -> int | None:
    """Align complete/skip with the plan-scoped ledger used by resolve_daily_mission."""
    if plan_id is not None:
        return plan_id
    existing = (
        await db.execute(
            select(StudentDailyTaskLedger)
            .where(
                StudentDailyTaskLedger.student_id == user.id,
                StudentDailyTaskLedger.local_date == today,
                StudentDailyTaskLedger.task_key == task_key,
            )
            .order_by(StudentDailyTaskLedger.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing.plan_id
    if task_key.startswith("baseline-") or task_key in ("generate_plan",):
        return None
    ready = await _latest_ready_plan(db, user.id)
    return ready.id if ready else None


TOOL_HREF = {
    "aptitude": "/studentportal/tools/aptitude?from=journey",
    "coding": "/studentportal/tools/coding?from=journey",
    "skill_readiness": "/studentportal/tools/skill_readiness?from=journey",
    "skill_mock": "/studentportal/tools/skill_mock?from=journey",
    "project_mock": "/studentportal/tools/project_mock?from=journey",
    "interview_readiness": "/studentportal/tools/interview_readiness?from=journey",
    "interview_mock": "/studentportal/tools/interview_mock?from=journey",
    "hr_mock": "/studentportal/tools/hr_mock?from=journey",
    "resume_ats": "/studentportal/tools/resume_ats?from=journey",
    "5_sec": "/studentportal/tools/5_sec?from=journey",
}


def _tool_href(
    tool_code: str,
    *,
    task_key: str | None = None,
    topic_nodes: list[str] | None = None,
) -> str:
    base = TOOL_HREF.get(tool_code) or f"/studentportal/tools/{quote(tool_code)}?from=journey"
    parts: list[str] = []
    if task_key:
        parts.append(f"mission={quote(str(task_key), safe='')}")
    if topic_nodes:
        parts.append(f"topics={quote(','.join(topic_nodes), safe=',')}")
    if not parts:
        return base
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}{'&'.join(parts)}"

PILLAR_DEFAULT_TOOL = {
    "aptitude": "aptitude",
    "coding": "coding",
    "technical": "skill_readiness",
    "communication": "skill_mock",
    "hr": "hr_mock",
    "resume": "resume_ats",
}


async def get_or_create_target(db: AsyncSession, user: User) -> StudentTarget:
    row = (
        await db.execute(select(StudentTarget).where(StudentTarget.student_id == user.id))
    ).scalar_one_or_none()
    if row:
        return row
    try:
        async with db.begin_nested():
            row = StudentTarget(
                student_id=user.id,
                target_companies=[],
                target_tier="mass_recruiter",
                target_readiness=DEFAULT_TARGET,
            )
            db.add(row)
            await db.flush()
    except IntegrityError:
        row = (
            await db.execute(select(StudentTarget).where(StudentTarget.student_id == user.id))
        ).scalar_one()
    return row


def target_to_dict(row: StudentTarget) -> dict[str, Any]:
    return {
        "target_companies": list(row.target_companies or []),
        "target_tier": row.target_tier,
        "target_readiness": row.target_readiness,
        "starting_level": row.starting_level or "some_experience",
        "baseline_path": row.baseline_path,
        "daily_budget_minutes": int(row.daily_budget_minutes or 25),
        "onboarding_completed": row.onboarding_completed_at is not None,
        "baseline_sprint_start_date": (
            row.baseline_sprint_start_date.isoformat()
            if row.baseline_sprint_start_date
            else None
        ),
    }


async def upsert_target(
    db: AsyncSession,
    user: User,
    *,
    target_companies: list[str],
    target_tier: str,
    target_readiness: int,
    starting_level: str = "some_experience",
    baseline_path: str | None = None,
    daily_budget_minutes: int = 25,
    onboarding_completed: bool = False,
) -> StudentTarget:
    row = await get_or_create_target(db, user)
    row.target_companies = list(target_companies or [])
    row.target_tier = target_tier or "mass_recruiter"
    row.target_readiness = int(target_readiness or DEFAULT_TARGET)
    row.starting_level = starting_level or "some_experience"
    if baseline_path is not None:
        row.baseline_path = baseline_path
    row.daily_budget_minutes = int(daily_budget_minutes or 25)
    if onboarding_completed and row.onboarding_completed_at is None:
        row.onboarding_completed_at = datetime.now(timezone.utc)
    if onboarding_completed and row.baseline_sprint_start_date is None:
        from app.student_roadmap.baseline_sprint import campus_today

        row.baseline_sprint_start_date = campus_today()
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def patch_target_baseline_path(
    db: AsyncSession, user: User, baseline_path: str
) -> StudentTarget:
    row = await get_or_create_target(db, user)
    row.baseline_path = baseline_path
    row.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return row


async def remember_fact(
    db: AsyncSession,
    student_id: int,
    *,
    fact: str,
    fact_type: str = "insight",
    topic_id: str | None = None,
    confidence: float = 0.75,
) -> None:
    """Upsert an active memory fact (used by mentor + future personalization)."""
    text = str(fact or "").strip()
    if not text:
        return
    now = datetime.now(timezone.utc)
    q = select(StudentMemoryFact).where(
        StudentMemoryFact.student_id == student_id,
        StudentMemoryFact.fact_type == fact_type,
        StudentMemoryFact.resolved_at.is_(None),
    )
    if topic_id:
        q = q.where(StudentMemoryFact.topic_id == topic_id)
    else:
        q = q.where(StudentMemoryFact.fact == text)
    existing = (await db.execute(q.limit(1))).scalar_one_or_none()
    if existing:
        existing.fact = text
        existing.confidence = Decimal(str(min(1.0, confidence + 0.05 * existing.evidence_count)))
        existing.evidence_count = int(existing.evidence_count or 0) + 1
        existing.last_observed = now
        existing.updated_at = now
        return
    db.add(
        StudentMemoryFact(
            student_id=student_id,
            fact_type=fact_type,
            topic_id=topic_id,
            fact=text,
            confidence=Decimal(str(confidence)),
            evidence_count=1,
            last_observed=now,
        )
    )


async def sync_roadmap_step_memory(
    db: AsyncSession,
    user: User,
    *,
    tool_code: str,
    strengths: list[str],
    weaknesses: list[str],
    score: float | None,
) -> None:
    """Persist baseline strengths/weaknesses into student_memory for mentor context."""
    if score is not None:
        await remember_fact(
            db,
            user.id,
            fact=f"Scored {int(round(score))}% on {tool_code.replace('_', ' ')} baseline check.",
            fact_type="baseline_score",
            topic_id=tool_code,
            confidence=0.9,
        )
    for w in (weaknesses or [])[:5]:
        wtext = str(w).strip()
        if not wtext:
            continue
        await remember_fact(
            db,
            user.id,
            fact=f"Gap to close: {wtext}",
            fact_type="weakness",
            topic_id=tool_code,
            confidence=0.85,
        )
    for s in (strengths or [])[:3]:
        stext = str(s).strip()
        if not stext:
            continue
        await remember_fact(
            db,
            user.id,
            fact=f"Strength: {stext}",
            fact_type="strength",
            topic_id=tool_code,
            confidence=0.8,
        )


async def _completion_rate_7d(db: AsyncSession, student_id: int, today: date) -> float:
    start = today - timedelta(days=6)
    rows = (
        await db.execute(
            select(StudentDailyActivity).where(
                StudentDailyActivity.student_id == student_id,
                StudentDailyActivity.local_date >= start,
                StudentDailyActivity.local_date <= today,
            )
        )
    ).scalars().all()
    if not rows:
        return 0.0
    done_days = sum(1 for r in rows if r.tasks_total > 0 and r.tasks_done >= r.tasks_total)
    return done_days / 7.0


def _attempt_dict(
    *,
    tool_code: str,
    score: float,
    technical_score: float | None,
    communication_score: float | None,
    completed_at: str | None,
) -> dict[str, Any]:
    return {
        "tool_code": tool_code,
        "score": score,
        "technical_score": technical_score,
        "communication_score": communication_score,
        "completed_at": completed_at,
    }


async def _attempts_for_readiness(db: AsyncSession, student_id: int) -> list[dict[str, Any]]:
    """Merge all scored attempts with Week-1 roadmap scores.

    Keep the full attempt time series (not one row per tool) so pillar scores
    and trends move as the student practices week to week. Roadmap step scores
    fill gaps only when that tool has never been attempted.
    """
    out: list[dict[str, Any]] = []
    seen_tools: set[str] = set()

    rows = (
        await db.execute(
            select(StudentAttempt)
            .where(StudentAttempt.student_id == student_id)
            .order_by(StudentAttempt.completed_at.asc().nulls_last())
        )
    ).scalars().all()
    for r in rows:
        if r.score is None or not r.tool_code:
            continue
        seen_tools.add(r.tool_code)
        out.append(
            _attempt_dict(
                tool_code=r.tool_code,
                score=float(r.score),
                technical_score=float(r.technical_score) if r.technical_score is not None else None,
                communication_score=float(r.communication_score)
                if r.communication_score is not None
                else None,
                completed_at=r.completed_at.isoformat() if r.completed_at else None,
            )
        )

    steps = (
        await db.execute(
            select(StudentRoadmapStep)
            .join(StudentRoadmapWeek, StudentRoadmapStep.week_id == StudentRoadmapWeek.id)
            .where(
                StudentRoadmapWeek.user_id == student_id,
                StudentRoadmapStep.status == "done",
                StudentRoadmapStep.score.is_not(None),
            )
        )
    ).scalars().all()
    for s in steps:
        if not s.tool_code or s.tool_code in seen_tools:
            continue
        seen_tools.add(s.tool_code)
        out.append(
            _attempt_dict(
                tool_code=s.tool_code,
                score=float(s.score),
                technical_score=float(s.technical_score) if s.technical_score is not None else None,
                communication_score=float(s.communication_score)
                if s.communication_score is not None
                else None,
                completed_at=s.completed_at.isoformat() if s.completed_at else None,
            )
        )

    return out


async def get_readiness(
    db: AsyncSession, user: User, *, local_date: str | None = None
) -> dict[str, Any]:
    today = _parse_date(local_date)
    target = await get_or_create_target(db, user)
    attempts = await _attempts_for_readiness(db, user.id)
    rate = await _completion_rate_7d(db, user.id, today)
    result = compute_readiness(
        {
            "attempts": attempts,
            "today": today.isoformat(),
            "completionRate7d": rate,
            "targetTier": target.target_tier,
            "targetCompanies": list(target.target_companies or []),
            "target": target.target_readiness,
        }
    )

    # Upsert daily snapshot (race-safe against concurrent dashboard requests).
    # Never overwrite a demo-seeded day — that would turn fake history into "real".
    snap = (
        await db.execute(
            select(StudentReadinessSnapshot).where(
                StudentReadinessSnapshot.student_id == user.id,
                StudentReadinessSnapshot.snapshot_date == today,
            )
        )
    ).scalar_one_or_none()
    if snap is not None and isinstance(snap.pillars, dict) and snap.pillars.get("_demo_seed"):
        return result
    if snap is None:
        try:
            async with db.begin_nested():
                snap = StudentReadinessSnapshot(student_id=user.id, snapshot_date=today)
                db.add(snap)
                await db.flush()
        except IntegrityError:
            snap = (
                await db.execute(
                    select(StudentReadinessSnapshot).where(
                        StudentReadinessSnapshot.student_id == user.id,
                        StudentReadinessSnapshot.snapshot_date == today,
                    )
                )
            ).scalar_one()
            if isinstance(snap.pillars, dict) and snap.pillars.get("_demo_seed"):
                return result
    snap.overall = result["overall"]
    snap.base = result["base"]
    snap.execution_multiplier = Decimal(str(result["execution_multiplier"]))
    snap.coverage = Decimal(str(result["coverage"]))
    snap.measured_pillars = result["measured_pillars"]
    snap.total_pillars = result["total_pillars"]
    snap.eta_days = result["eta_days"]
    snap.pillars = result["pillars"]
    snap.focus_pillar = result["focus_pillar"]
    snap.weakest_pillar = result["weakest_pillar"]
    snap.gates = result["gates"]
    await db.flush()
    return result


async def list_mastery(
    db: AsyncSession, user: User, *, due_before: str | None = None
) -> list[dict[str, Any]]:
    q = select(StudentTopicMastery).where(StudentTopicMastery.student_id == user.id)
    if due_before:
        due = _parse_date(due_before)
        q = q.where(
            StudentTopicMastery.next_review_at.is_not(None),
            StudentTopicMastery.next_review_at <= due,
        )
    rows = (await db.execute(q)).scalars().all()
    today = _campus_today()
    out = []
    for row in rows:
        m = row_to_mastery(row, today)
        out.append(
            {
                "topic_id": m["topic_id"],
                "recognition": {
                    "level": m["modalities"]["recognition"]["level"],
                    "attempts": m["modalities"]["recognition"]["attempts"],
                    "consecutive_passes": m["modalities"]["recognition"]["consecutivePasses"],
                    "last_at": m["modalities"]["recognition"]["lastAttemptAt"],
                },
                "application": {
                    "level": m["modalities"]["application"]["level"],
                    "attempts": m["modalities"]["application"]["attempts"],
                    "consecutive_passes": m["modalities"]["application"]["consecutivePasses"],
                    "last_at": m["modalities"]["application"]["lastAttemptAt"],
                },
                "explanation": {
                    "level": m["modalities"]["explanation"]["level"],
                    "attempts": m["modalities"]["explanation"]["attempts"],
                    "consecutive_passes": m["modalities"]["explanation"]["consecutivePasses"],
                    "last_at": m["modalities"]["explanation"]["lastAttemptAt"],
                },
                "assessed_at": m["assessedAt"],
                "next_review_at": m["nextReviewAt"],
            }
        )
    return out


async def list_memory(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(StudentMemoryFact).where(
                StudentMemoryFact.student_id == user.id,
                StudentMemoryFact.resolved_at.is_(None),
            )
        )
    ).scalars().all()
    return [
        {
            "fact_type": r.fact_type,
            "topic_id": r.topic_id,
            "fact": r.fact,
            "confidence": float(r.confidence),
            "evidence_count": r.evidence_count,
            "last_observed": r.last_observed.isoformat() if r.last_observed else None,
        }
        for r in rows
    ]


async def get_coverage(db: AsyncSession, user: User) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(StudentCoverageLedger).where(StudentCoverageLedger.student_id == user.id)
        )
    ).scalars().all()
    ledger = ledger_from_rows(rows)
    tested = {
        tid: {
            "pool": e["pool"],
            "attempts": e["attempts"],
            "correct": e["correct"],
            "last_tested_at": e["lastTestedAt"],
        }
        for tid, e in ledger["tested"].items()
    }
    return {
        "tested": tested,
        "in_retry": sorted(ledger["in_retry"]),
        "in_verify": sorted(ledger["in_verify"]),
    }


async def _mastery_map(db: AsyncSession, student_id: int) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(StudentTopicMastery).where(StudentTopicMastery.student_id == student_id)
        )
    ).scalars().all()
    today = _campus_today()
    return {r.topic_id: row_to_mastery(r, today) for r in rows}


async def _ensure_anchor(
    db: AsyncSession, user: User, plan_id: int | None, today: date
) -> date:
    row = (
        await db.execute(
            select(StudentMissionAnchor).where(
                StudentMissionAnchor.student_id == user.id,
                _plan_id_match(StudentMissionAnchor.plan_id, plan_id),
            )
        )
    ).scalar_one_or_none()
    if row:
        return row.anchor_date
    try:
        async with db.begin_nested():
            row = StudentMissionAnchor(student_id=user.id, plan_id=plan_id, anchor_date=today)
            db.add(row)
            await db.flush()
        return today
    except IntegrityError:
        row = (
            await db.execute(
                select(StudentMissionAnchor).where(
                    StudentMissionAnchor.student_id == user.id,
                    _plan_id_match(StudentMissionAnchor.plan_id, plan_id),
                )
            )
        ).scalar_one()
        return row.anchor_date


def _day_in_plan(anchor: date, today: date, horizon: int = PLAN_HORIZON_MAX) -> int:
    return max(1, min(horizon, (today - anchor).days + 1))


def _why_this(topic_id: str, pool: str, focus_pillar: str | None) -> str:
    if pool == "VERIFY":
        return f"Quick recheck — {topic_id} was mastered earlier. Let's see if it stuck."
    if pool == "RETRY":
        return f"You struggled with {topic_id} before. Today's task narrows in on that gap."
    if focus_pillar:
        return f"New coverage for {topic_id} — focus pillar today is {focus_pillar}."
    return f"New topic on your map: {topic_id}."


async def _load_week1(db: AsyncSession, user_id: int) -> StudentRoadmapWeek | None:
    return (
        await db.execute(
            select(StudentRoadmapWeek)
            .where(
                StudentRoadmapWeek.user_id == user_id,
                StudentRoadmapWeek.week_number == WEEK1_NUMBER,
            )
            .options(selectinload(StudentRoadmapWeek.steps))
        )
    ).scalar_one_or_none()


async def _latest_ready_plan(
    db: AsyncSession, user_id: int
) -> StudentGeneratedRoadmap | None:
    return (
        await db.execute(
            select(StudentGeneratedRoadmap)
            .where(
                StudentGeneratedRoadmap.user_id == user_id,
                StudentGeneratedRoadmap.status == PLAN_STATUS_READY,
            )
            .order_by(StudentGeneratedRoadmap.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _empty_mission(
    *,
    mode: str,
    today: date,
    tasks: list[dict[str, Any]],
    budget_minutes: int,
    day_in_plan: int | None = None,
    focus_pillar: str | None = None,
    plan_id: int | None = None,
) -> dict[str, Any]:
    required = [t for t in tasks if t.get("required", True)]
    done_count = sum(1 for t in required if t.get("done") or t.get("status") == "done")
    total_minutes = sum(int(t.get("minutes") or 0) for t in tasks)
    return {
        "mode": mode,
        "day_in_plan": day_in_plan,
        "plan_id": plan_id,
        "anchor_date": None,
        "local_date": today.isoformat(),
        "phase": None,
        "tasks": tasks,
        "requiredCount": len(required),
        "doneCount": done_count,
        "complete": done_count >= len(required) and len(required) > 0,
        "totalMinutes": total_minutes,
        "budgetMinutes": budget_minutes,
        "completionRate7d": 0.0,
        "focus_pillar": focus_pillar,
        "slate": [],
        "compressedDays": [],
        "droppedTasks": [],
        "fallback_reason": None,
        "plan_day_empty": False,
    }


async def resolve_daily_mission(
    db: AsyncSession,
    user: User,
    *,
    local_date: str | None = None,
    budget_minutes: int = 25,
    plan_id: int | None = None,
    focus_pillar: str | None = None,
) -> dict[str, Any]:
    today = _parse_date(local_date)

    # Week-1 baseline owns Today until every step is done.
    week = await _load_week1(db, user.id)
    if week is None or week.status != WEEK_STATUS_DONE:
        current = next(
            (s for s in (week.steps if week else []) if s.status == STEP_STATUS_CURRENT),
            None,
        )
        tasks: list[dict[str, Any]] = []
        if current:
            meta = TOOL_META.get(current.tool_code) or {}
            minutes = int(meta.get("minutes") or 15)
            href = meta.get("href") or _tool_href(current.tool_code)
            tasks.append(
                {
                    "task_key": f"baseline-{current.tool_code}",
                    "text": meta.get("title") or current.tool_code,
                    "title": meta.get("title") or current.tool_code,
                    "required": True,
                    "minutes": minutes,
                    "done": False,
                    "status": "todo",
                    "kind": "tool",
                    "tool_code": current.tool_code,
                    "tool_href": href,
                    "why_this": "Finish Week-1 baseline to unlock your placement plan.",
                }
            )
        return _empty_mission(
            mode="baseline",
            today=today,
            tasks=tasks,
            budget_minutes=budget_minutes,
            focus_pillar=focus_pillar,
        )

    ready_plan = await _latest_ready_plan(db, user.id)
    if ready_plan is None:
        return _empty_mission(
            mode="awaiting_plan",
            today=today,
            tasks=[
                {
                    "task_key": "generate_plan",
                    "text": "Generate your personalized placement plan",
                    "title": "Generate your personalized placement plan",
                    "required": True,
                    "minutes": 2,
                    "done": False,
                    "status": "todo",
                    "kind": "action",
                    "action": "generate_plan",
                    "tool_code": None,
                    "tool_href": None,
                    "why_this": "Assessment week is done — build your 30–45 day plan from it.",
                }
            ],
            budget_minutes=budget_minutes,
            focus_pillar=focus_pillar,
        )

    effective_plan_id = plan_id if plan_id is not None else ready_plan.id

    target = await get_or_create_target(db, user)
    if focus_pillar:
        focus = focus_pillar
    else:
        readiness = await get_readiness(db, user, local_date=today.isoformat())
        focus = readiness.get("focus_pillar") or "aptitude"
    anchor = await _ensure_anchor(db, user, effective_plan_id, today)

    plan_payload = ready_plan.plan_json if isinstance(ready_plan.plan_json, dict) else {}
    plan_root = plan_payload.get("plan") if isinstance(plan_payload.get("plan"), dict) else plan_payload
    horizon = plan_horizon_from_plan_json(plan_root)
    day_n = _day_in_plan(anchor, today, horizon)

    coverage_rows = (
        await db.execute(
            select(StudentCoverageLedger).where(StudentCoverageLedger.student_id == user.id)
        )
    ).scalars().all()
    ledger = ledger_from_rows(coverage_rows)
    mastery = await _mastery_map(db, user.id)
    pruned = prune_syllabus_for_companies(
        get_all_topics(), list(target.target_companies or [])
    )
    if not pruned:
        pruned = [t["id"] for t in get_all_topics()]

    num_q = 2 if budget_minutes >= 35 else 1
    topics = select_slate(
        day_in_plan=day_n,
        num_questions_needed=num_q,
        ledger=ledger,
        topic_mastery=mastery,
        pruned_syllabus=pruned,
    )

    focus = readiness.get("focus_pillar") or "aptitude"

    plan_index = build_day_index(plan_root)
    plan_entry = plan_index.get(day_n)
    plan_tasks = tasks_for_plan_day(plan_entry, day_n=day_n, focus_pillar=focus)

    existing = (
        await db.execute(
            select(StudentDailyTaskLedger).where(
                StudentDailyTaskLedger.student_id == user.id,
                StudentDailyTaskLedger.local_date == today,
                _plan_id_match(StudentDailyTaskLedger.plan_id, effective_plan_id),
            )
        )
    ).scalars().all()
    done_keys = {e.task_key for e in existing if e.status == "done"}

    tasks: list[dict[str, Any]] = []
    total_minutes = 0
    mode = "intelligence"
    plan_day_empty = False
    fallback_reason: str | None = None

    if plan_tasks:
        mode = "plan"
        for t in plan_tasks:
            task_key = t["task_key"]
            done = task_key in done_keys
            t["done"] = done
            t["status"] = "done" if done else "todo"
            total_minutes += int(t.get("minutes") or 0)
            tasks.append(t)
    else:
        plan_day_empty = True
        fallback_reason = "empty_plan_day" if plan_entry is None else "empty_plan_tasks"
        tool_code = PILLAR_DEFAULT_TOOL.get(focus, "aptitude")
        for i, topic_id in enumerate(topics or [f"focus.{focus}"]):
            pool = (ledger["tested"].get(topic_id) or {}).get("pool") or "NEW"
            task_key = f"day{day_n}-{tool_code}-{topic_id}-{i}"
            minutes = min(20, max(10, budget_minutes // max(1, len(topics) or 1)))
            total_minutes += minutes
            topic_nodes = [topic_id] if not topic_id.startswith("focus.") else []
            widget = {
                "tool_code": tool_code,
                "topic_nodes": topic_nodes,
                "modality": TOOL_MODALITY.get(tool_code, "recognition"),
                "question_count": 8 if tool_code == "aptitude" else 1,
                "time_limit_s": minutes * 60,
                "difficulty": 2,
                "mastery_bar": 0.75,
                "attempt_number": 1,
                "why_this": _why_this(topic_id, pool, focus),
            }
            tasks.append(
                {
                    "task_key": task_key,
                    "text": f"Practice {topic_id.replace('.', ' · ')}",
                    "required": True,
                    "minutes": minutes,
                    "done": task_key in done_keys,
                    "tool_code": tool_code,
                    "tool_href": _tool_href(tool_code, task_key=task_key, topic_nodes=topic_nodes),
                    "widget_spec": widget,
                    "why_this": widget["why_this"],
                    "topic_nodes": widget["topic_nodes"],
                    "modality": widget["modality"],
                    "difficulty": widget["difficulty"],
                    "attempt_number": widget["attempt_number"],
                    "question_count": widget["question_count"],
                    "time_limit_s": widget["time_limit_s"],
                }
            )

    required = [t for t in tasks if t.get("required", True)]
    done_count = sum(1 for t in required if t.get("done"))
    rate = await _completion_rate_7d(db, user.id, today)

    activity = (
        await db.execute(
            select(StudentDailyActivity).where(
                StudentDailyActivity.student_id == user.id,
                StudentDailyActivity.local_date == today,
            )
        )
    ).scalar_one_or_none()
    if activity is None:
        try:
            async with db.begin_nested():
                activity = StudentDailyActivity(student_id=user.id, local_date=today)
                db.add(activity)
                await db.flush()
        except IntegrityError:
            activity = (
                await db.execute(
                    select(StudentDailyActivity).where(
                        StudentDailyActivity.student_id == user.id,
                        StudentDailyActivity.local_date == today,
                    )
                )
            ).scalar_one()
    activity.tasks_done = done_count
    activity.tasks_total = len(required)
    activity.minutes = total_minutes
    activity.completion_rate_7d = Decimal(str(round(rate, 4)))
    activity.updated_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "mode": mode,
        "day_in_plan": day_n,
        "plan_id": effective_plan_id,
        "anchor_date": anchor.isoformat(),
        "local_date": today.isoformat(),
        "phase": "prep" if day_n <= 35 else "practice",
        "deep_prep_days": 35,
        "tasks": tasks,
        "requiredCount": len(required),
        "doneCount": done_count,
        "complete": done_count >= len(required) and len(required) > 0,
        "totalMinutes": total_minutes,
        "budgetMinutes": budget_minutes,
        "completionRate7d": rate,
        "focus_pillar": focus,
        "slate": topics,
        "compressedDays": [],
        "droppedTasks": [],
        "theme": (plan_entry or {}).get("theme"),
        "week_ordinal": (plan_entry or {}).get("weekOrdinal"),
        "horizon": horizon,
        "fallback_reason": fallback_reason,
        "plan_day_empty": plan_day_empty,
    }


async def _rollup_today_activity(
    db: AsyncSession,
    student_id: int,
    today: date,
    *,
    minutes: int | None = None,
    plan_id: int | None = None,
) -> None:
    q = select(StudentDailyTaskLedger).where(
        StudentDailyTaskLedger.student_id == student_id,
        StudentDailyTaskLedger.local_date == today,
    )
    if plan_id is not None:
        q = q.where(StudentDailyTaskLedger.plan_id == plan_id)
    rows = (await db.execute(q)).scalars().all()
    done = sum(1 for r in rows if r.status == "done")
    rate = await _completion_rate_7d(db, student_id, today)
    activity = (
        await db.execute(
            select(StudentDailyActivity).where(
                StudentDailyActivity.student_id == student_id,
                StudentDailyActivity.local_date == today,
            )
        )
    ).scalar_one_or_none()
    if activity is None:
        try:
            async with db.begin_nested():
                activity = StudentDailyActivity(student_id=student_id, local_date=today)
                db.add(activity)
                await db.flush()
        except IntegrityError:
            activity = (
                await db.execute(
                    select(StudentDailyActivity).where(
                        StudentDailyActivity.student_id == student_id,
                        StudentDailyActivity.local_date == today,
                    )
                )
            ).scalar_one()
    # Ledger only has completed/skipped rows — never shrink slate size from resolve.
    prev_total = int(activity.tasks_total or 0)
    activity.tasks_done = done
    activity.tasks_total = max(prev_total, done)
    if minutes is not None:
        activity.minutes = minutes
    activity.completion_rate_7d = Decimal(str(round(rate, 4)))
    activity.updated_at = datetime.now(timezone.utc)
    await db.flush()


async def complete_task(
    db: AsyncSession,
    user: User,
    task_key: str,
    *,
    local_date: str | None = None,
    plan_id: int | None = None,
    score: float | None = None,
    text_hash: str | None = None,
    source: str = "manual",
    tool_code: str | None = None,
    topic_nodes: list[str] | None = None,
) -> dict[str, Any]:
    today = _parse_date(local_date)
    effective_plan_id = await _resolve_ledger_plan_id(db, user, today, task_key, plan_id)
    row = (
        await db.execute(
            select(StudentDailyTaskLedger).where(
                StudentDailyTaskLedger.student_id == user.id,
                StudentDailyTaskLedger.local_date == today,
                StudentDailyTaskLedger.task_key == task_key,
                _plan_id_match(StudentDailyTaskLedger.plan_id, effective_plan_id),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        try:
            async with db.begin_nested():
                row = StudentDailyTaskLedger(
                    student_id=user.id,
                    plan_id=effective_plan_id,
                    local_date=today,
                    task_key=task_key,
                    status="done",
                    source=source,
                    score=Decimal(str(score)) if score is not None else None,
                    text_hash=text_hash,
                )
                db.add(row)
                await db.flush()
        except IntegrityError:
            row = (
                await db.execute(
                    select(StudentDailyTaskLedger).where(
                        StudentDailyTaskLedger.student_id == user.id,
                        StudentDailyTaskLedger.local_date == today,
                        StudentDailyTaskLedger.task_key == task_key,
                        _plan_id_match(StudentDailyTaskLedger.plan_id, effective_plan_id),
                    )
                )
            ).scalar_one()
            row.status = "done"
            row.source = source
            if score is not None:
                row.score = Decimal(str(score))
            row.text_hash = text_hash
            await db.flush()
    else:
        row.status = "done"
        row.source = source
        if score is not None:
            row.score = Decimal(str(score))
        row.text_hash = text_hash
        await db.flush()
    await _rollup_today_activity(db, user.id, today, plan_id=effective_plan_id)

    # Bridge scored task completions into readiness attempts so pillars evolve week-to-week
    inferred_tool = tool_code or _infer_tool_from_task_key(task_key)
    attempt_recorded = False
    attempt_error: str | None = None
    if score is not None and inferred_tool:
        try:
            await record_attempt(
                db,
                user,
                {
                    "tool_code": inferred_tool,
                    "score": float(score),
                    "topic_nodes": list(topic_nodes or []),
                    "source": source,
                    "attempt_number": 1,
                },
            )
            attempt_recorded = True
        except Exception as exc:
            logger.exception(
                "record_attempt failed after task complete student=%s task=%s tool=%s",
                user.id,
                task_key,
                inferred_tool,
            )
            attempt_error = str(exc) or exc.__class__.__name__
    elif score is not None and not inferred_tool:
        attempt_error = "missing_tool_code"

    return {
        "ok": True,
        "task_key": task_key,
        "status": "done",
        "tool_code": inferred_tool,
        "plan_id": effective_plan_id,
        "attempt_recorded": attempt_recorded,
        "attempt_error": attempt_error,
    }


def _infer_tool_from_task_key(task_key: str) -> str | None:
    """Extract tool_code from keys like baseline-aptitude, plan-d12-coding-0, day3-coding-…"""
    key = (task_key or "").strip()
    if not key:
        return None
    if key.startswith("baseline-"):
        code = key[len("baseline-") :]
        return code if code in TOOL_PILLARS else None

    # plan-d{n}-{tool|manual}-{i}
    if key.startswith("plan-d"):
        parts = key.split("-")
        # ["plan", "d12", "coding", "0"] or ["plan", "d12", "0"] (legacy)
        if len(parts) >= 4:
            candidate = parts[2]
            if candidate in TOOL_PILLARS:
                return candidate
            if candidate != "manual":
                inferred = infer_tool_code(candidate.replace("_", " "))
                if inferred:
                    return inferred
        return None

    # Prefer longest tool_code match inside the key
    for code in sorted(TOOL_PILLARS.keys(), key=len, reverse=True):
        if code in key.split("-") or f"-{code}-" in f"-{key}-":
            return code
    return None


async def skip_task(
    db: AsyncSession,
    user: User,
    task_key: str,
    *,
    local_date: str | None = None,
    plan_id: int | None = None,
    reason: str = "manual",
    text_hash: str | None = None,
) -> dict[str, Any]:
    today = _parse_date(local_date)
    effective_plan_id = await _resolve_ledger_plan_id(db, user, today, task_key, plan_id)
    row = (
        await db.execute(
            select(StudentDailyTaskLedger).where(
                StudentDailyTaskLedger.student_id == user.id,
                StudentDailyTaskLedger.local_date == today,
                StudentDailyTaskLedger.task_key == task_key,
                _plan_id_match(StudentDailyTaskLedger.plan_id, effective_plan_id),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        try:
            async with db.begin_nested():
                row = StudentDailyTaskLedger(
                    student_id=user.id,
                    plan_id=effective_plan_id,
                    local_date=today,
                    task_key=task_key,
                    status="skipped",
                    source=reason,
                    text_hash=text_hash,
                )
                db.add(row)
                await db.flush()
        except IntegrityError:
            row = (
                await db.execute(
                    select(StudentDailyTaskLedger).where(
                        StudentDailyTaskLedger.student_id == user.id,
                        StudentDailyTaskLedger.local_date == today,
                        StudentDailyTaskLedger.task_key == task_key,
                        _plan_id_match(StudentDailyTaskLedger.plan_id, effective_plan_id),
                    )
                )
            ).scalar_one()
            row.status = "skipped"
            row.source = reason
            row.text_hash = text_hash
            await db.flush()
    else:
        row.status = "skipped"
        row.source = reason
        row.text_hash = text_hash
        await db.flush()
    await _rollup_today_activity(db, user.id, today, plan_id=effective_plan_id)
    return {
        "ok": True,
        "task_key": task_key,
        "status": "skipped",
        "plan_id": effective_plan_id,
    }


async def record_attempt(db: AsyncSession, user: User, body: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    completed_at = now
    if body.get("completed_at"):
        try:
            completed_at = datetime.fromisoformat(
                str(body["completed_at"]).replace("Z", "+00:00")
            )
        except Exception:
            completed_at = now

    attempt = StudentAttempt(
        student_id=user.id,
        tool_code=body.get("tool_code"),
        widget_spec=body.get("widget_spec"),
        topic_nodes=list(body.get("topic_nodes") or []),
        modality=body.get("modality") or TOOL_MODALITY.get(body.get("tool_code") or "", "recognition"),
        difficulty=body.get("difficulty"),
        score=Decimal(str(body["score"])) if body.get("score") is not None else None,
        accuracy=Decimal(str(body["accuracy"])) if body.get("accuracy") is not None else None,
        time_taken_s=body.get("time_taken_s"),
        technical_score=Decimal(str(body["technical_score"]))
        if body.get("technical_score") is not None
        else None,
        communication_score=Decimal(str(body["communication_score"]))
        if body.get("communication_score") is not None
        else None,
        mistakes=list(body.get("mistakes") or []),
        attempt_number=body.get("attempt_number") or 1,
        item_embeddings=body.get("item_embeddings"),
        transcript_ref=body.get("transcript_ref"),
        completed_at=completed_at,
    )
    db.add(attempt)

    accuracy = float(body["accuracy"]) if body.get("accuracy") is not None else (
        float(body["score"]) / 100.0 if body.get("score") is not None else 0.0
    )
    within_time = bool(body.get("within_time", True))
    modality = attempt.modality or "recognition"
    # After an attempt, topic is never NEW — only RETRY or VERIFY (slate starvation bug).
    requested_pool = body.get("pool")
    if requested_pool not in ("RETRY", "VERIFY"):
        requested_pool = "RETRY"

    for topic_id in attempt.topic_nodes or []:
        # Mastery
        mrow = (
            await db.execute(
                select(StudentTopicMastery).where(
                    StudentTopicMastery.student_id == user.id,
                    StudentTopicMastery.topic_id == topic_id,
                )
            )
        ).scalar_one_or_none()
        if mrow is None:
            mrow = StudentTopicMastery(student_id=user.id, topic_id=topic_id)
            db.add(mrow)
            await db.flush()
        mastery = row_to_mastery(mrow)
        update_mastery(
            mastery,
            modality=modality,
            accuracy=accuracy,
            within_time=within_time,
            attempted_at=completed_at.isoformat(),
        )
        max_level = max(
            mastery["modalities"][m]["level"] for m in ("recognition", "application", "explanation")
        )
        topic_pool = "VERIFY" if max_level >= 3 else requested_pool
        if topic_pool == "VERIFY":
            schedule_next_review(mastery, completed_at.date())
        apply_mastery_to_row(mrow, mastery)
        mrow.updated_at = now

        # Coverage
        crow = (
            await db.execute(
                select(StudentCoverageLedger).where(
                    StudentCoverageLedger.student_id == user.id,
                    StudentCoverageLedger.topic_id == topic_id,
                )
            )
        ).scalar_one_or_none()
        if crow is None:
            crow = StudentCoverageLedger(
                student_id=user.id,
                topic_id=topic_id,
                pool=topic_pool,
                first_tested_at=completed_at,
                last_tested_at=completed_at,
                attempts=1,
                correct=1 if accuracy >= 0.6 else 0,
                never_return_to_new=True,
            )
            db.add(crow)
        else:
            crow.pool = topic_pool
            crow.last_tested_at = completed_at
            crow.attempts = int(crow.attempts or 0) + 1
            if accuracy >= 0.6:
                crow.correct = int(crow.correct or 0) + 1
            crow.never_return_to_new = True
            crow.updated_at = now

    await db.flush()
    return {"ok": True, "attempt_id": attempt.id}
