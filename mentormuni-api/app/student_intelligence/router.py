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
    return StudentTargetOut(
        target_companies=list(row.target_companies or []),
        target_tier=row.target_tier,
        target_readiness=row.target_readiness,
    )


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
    )
    return StudentTargetOut(
        target_companies=list(row.target_companies or []),
        target_tier=row.target_tier,
        target_readiness=row.target_readiness,
    )


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
