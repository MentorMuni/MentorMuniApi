"""Student Intelligence P0 routes — student portal only."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key, require_roles
from app.models.enums import RoleCode
from app.models.user import User
from app.student_intelligence import service as intel_service
from app.student_intelligence.schemas import (
    AttemptIn,
    DailyMissionSummaryOut,
    GatesSummaryOut,
    PlanProgressOut,
    ReadinessHistoryOut,
    StudentPerformanceDashboardOut,
    StudentTargetIn,
    StudentTargetOut,
    TaskCompleteIn,
    TaskSkipIn,
)

router = APIRouter(
    tags=["Student Intelligence"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/student/readiness")
async def get_readiness(
    local_date: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> dict[str, Any]:
    return await intel_service.get_readiness(db, user, local_date=local_date)


@router.get("/student/readiness/history", response_model=ReadinessHistoryOut)
async def get_readiness_history(
    days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> ReadinessHistoryOut:
    from app.student_intelligence.history import get_readiness_history as _history

    return await _history(db, student_id=user.id, days=days)


@router.get("/student/performance/dashboard", response_model=StudentPerformanceDashboardOut)
async def get_performance_dashboard(
    local_date: Optional[str] = Query(None),
    days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> StudentPerformanceDashboardOut:
    from app.student_intelligence.history import (
        build_cumulative_analysis,
        build_daily_mission_summary,
        build_gates_summary,
        build_performance_insights,
        build_plan_progress,
        get_readiness_history as _history,
    )
    from app.student_roadmap import service as roadmap_service

    readiness = await intel_service.get_readiness(db, user, local_date=local_date)
    campus_today = intel_service._parse_date(local_date)
    history = await _history(
        db, student_id=user.id, days=days, anchor_date=campus_today,
    )
    baseline = await roadmap_service.get_analysis(db, user)
    cumulative = await build_cumulative_analysis(
        db,
        student_id=user.id,
        baseline_analysis=baseline.model_dump(),
    )
    insights = build_performance_insights(readiness, cumulative)
    target_row = await intel_service.get_or_create_target(db, user)
    roadmap = await roadmap_service.get_roadmap(db, user)
    daily = await intel_service.resolve_daily_mission(
        db,
        user,
        local_date=local_date,
        budget_minutes=int(target_row.daily_budget_minutes or 25),
        focus_pillar=readiness.get("focus_pillar"),
    )
    mission_summary = build_daily_mission_summary(daily)
    return StudentPerformanceDashboardOut(
        readiness=readiness,
        history=history,
        insights=insights,
        target=StudentTargetOut(**intel_service.target_to_dict(target_row)),
        roadmap=roadmap.model_dump(),
        gates_summary=GatesSummaryOut(**build_gates_summary(readiness.get("gates"))),
        daily_mission=DailyMissionSummaryOut(**mission_summary),
        plan_progress=PlanProgressOut(**build_plan_progress(daily, mission_summary)),
    )


@router.get("/student/mastery")
async def get_mastery(
    due_before: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> list[dict[str, Any]]:
    return await intel_service.list_mastery(db, user, due_before=due_before)


@router.get("/student/memory")
async def get_memory(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> list[dict[str, Any]]:
    return await intel_service.list_memory(db, user)


@router.get("/student/coverage")
async def get_coverage(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> dict[str, Any]:
    return await intel_service.get_coverage(db, user)


@router.get("/student/target", response_model=StudentTargetOut)
async def get_target(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> StudentTargetOut:
    row = await intel_service.get_or_create_target(db, user)
    return StudentTargetOut(**intel_service.target_to_dict(row))


@router.post("/student/target", response_model=StudentTargetOut)
async def post_target(
    body: StudentTargetIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> StudentTargetOut:
    row = await intel_service.upsert_target(
        db,
        user,
        target_companies=body.target_companies,
        target_tier=body.target_tier,
        target_readiness=body.target_readiness,
        starting_level=body.starting_level,
        baseline_path=body.baseline_path,
        daily_budget_minutes=body.daily_budget_minutes,
        onboarding_completed=body.onboarding_completed,
    )
    await db.commit()
    return StudentTargetOut(**intel_service.target_to_dict(row))


@router.get("/student/daily")
async def get_daily(
    local_date: Optional[str] = Query(None),
    tz_offset_minutes: int = Query(0),
    budget_minutes: int = Query(25),
    plan_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> dict[str, Any]:
    _ = tz_offset_minutes
    return await intel_service.resolve_daily_mission(
        db,
        user,
        local_date=local_date,
        budget_minutes=budget_minutes,
        plan_id=plan_id,
    )


@router.post("/student/daily/tasks/{task_key}/complete")
async def complete_daily_task(
    task_key: str,
    body: TaskCompleteIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> dict[str, Any]:
    return await intel_service.complete_task(
        db,
        user,
        task_key,
        local_date=body.local_date,
        plan_id=body.plan_id,
        score=body.score,
        text_hash=body.text_hash,
        source=body.source or "manual",
        tool_code=body.tool_code,
        topic_nodes=body.topic_nodes,
    )


@router.post("/student/daily/tasks/{task_key}/skip")
async def skip_daily_task(
    task_key: str,
    body: TaskSkipIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> dict[str, Any]:
    return await intel_service.skip_task(
        db,
        user,
        task_key,
        local_date=body.local_date,
        plan_id=body.plan_id,
        reason=body.reason or "manual",
        text_hash=body.text_hash,
    )


@router.post("/student/attempts")
async def post_attempt(
    body: AttemptIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.STUDENT.value)),
) -> dict[str, Any]:
    return await intel_service.record_attempt(db, user, body.model_dump())
