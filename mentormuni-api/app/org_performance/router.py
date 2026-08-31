"""Organization performance analytics routes (TPO campus / HOD department)."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.org_performance import service as perf_service
from app.notifications import service as notif_service
from app.org_performance.insight import generate_insight, generate_student_insight
from app.org_performance.notify import notify_performance_cohort
from app.org_performance.schemas import (
    InsightOut,
    InsightRequest,
    NotifyCohortOut,
    NotifyCohortRequest,
    PerformanceSummaryOut,
    PerformanceTrendsOut,
    ScorecardListOut,
    StudentInsightOut,
    StudentInsightRequest,
    StudentScorecard,
)
from app.org_performance.snapshots import get_performance_trends

router = APIRouter(
    prefix="/organizations/performance",
    tags=["Organization Performance"],
    dependencies=[Depends(require_api_key)],
)

ai_router = APIRouter(
    prefix="/organizations/ai",
    tags=["Organization AI Insight"],
    dependencies=[Depends(require_api_key)],
)


@router.get("/summary", response_model=PerformanceSummaryOut)
async def performance_summary(
    department_id: int | None = Query(default=None),
    board_limit: int = Query(default=10, ge=3, le=50),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("VIEW_REPORTS", "VIEW_ALL_STUDENTS", "VIEW_DEPARTMENT_STUDENTS")
    ),
) -> PerformanceSummaryOut:
    if not ctx.sees_all_students and department_id is not None:
        if ctx.department_id is None or int(department_id) != int(ctx.department_id):
            raise HTTPException(status_code=403, detail="HOD can only view their own department.")
    return await perf_service.get_performance_summary(
        db, ctx, department_id=department_id, board_limit=board_limit
    )


@router.get("/scorecards", response_model=ScorecardListOut)
async def performance_scorecards(
    department_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("VIEW_REPORTS", "VIEW_ALL_STUDENTS", "VIEW_DEPARTMENT_STUDENTS")
    ),
) -> ScorecardListOut:
    if not ctx.sees_all_students and department_id is not None:
        if ctx.department_id is None or int(department_id) != int(ctx.department_id):
            raise HTTPException(status_code=403, detail="HOD can only view their own department.")
    return await perf_service.list_scorecards(db, ctx, department_id=department_id)


@router.get("/scorecards/{student_id}", response_model=StudentScorecard)
async def performance_student_scorecard(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("VIEW_REPORTS", "VIEW_ALL_STUDENTS", "VIEW_DEPARTMENT_STUDENTS")
    ),
) -> StudentScorecard:
    return await perf_service.get_student_scorecard(db, ctx, student_id)


@router.get("/trends", response_model=PerformanceTrendsOut)
async def performance_trends(
    department_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("VIEW_REPORTS", "VIEW_ALL_STUDENTS", "VIEW_DEPARTMENT_STUDENTS")
    ),
) -> PerformanceTrendsOut:
    if not ctx.sees_all_students and department_id is not None:
        if ctx.department_id is None or int(department_id) != int(ctx.department_id):
            raise HTTPException(status_code=403, detail="HOD can only view their own department.")
    dept_id = department_id
    if not ctx.sees_all_students:
        dept_id = ctx.department_id
    return await get_performance_trends(
        db,
        organization_id=ctx.organization_id,
        department_id=dept_id,
        days=days,
    )


@router.post("/notify-cohort", response_model=NotifyCohortOut)
async def performance_notify_cohort(
    body: NotifyCohortRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("SEND_NOTIFICATION", "VIEW_ALL_STUDENTS", "VIEW_DEPARTMENT_STUDENTS")
    ),
) -> NotifyCohortOut:
    """Notify a performance cohort (inactive, at-risk, etc.) via in-app + email."""
    from app.org_performance.service import PerformanceError

    try:
        return await notify_performance_cohort(
            db, ctx, body, background_tasks=background_tasks
        )
    except PerformanceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    except notif_service.NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@ai_router.post("/campus-insight", response_model=InsightOut)
async def campus_insight(
    body: InsightRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("VIEW_ALL_STUDENTS", "VIEW_REPORTS")),
) -> InsightOut:
    """TPO campus deep analysis brief (OpenAI + aggregates). Optional department filter."""
    if not ctx.sees_all_students:
        raise HTTPException(
            status_code=403,
            detail="Campus insight is for TPO / org admins. HODs should use branch-insight.",
        )
    req = body or InsightRequest()
    summary = await perf_service.get_performance_summary(
        db, ctx, department_id=req.department_id
    )
    return await generate_insight(summary, req)


@ai_router.post("/branch-insight", response_model=InsightOut)
async def branch_insight(
    body: InsightRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("VIEW_DEPARTMENT_STUDENTS", "VIEW_REPORTS")
    ),
) -> InsightOut:
    """HOD (or TPO with department_id) deep analysis brief for one branch."""
    req = body or InsightRequest()
    if ctx.sees_all_students:
        if req.department_id is None:
            raise HTTPException(
                status_code=400,
                detail="department_id is required for TPO branch-insight. Use campus-insight for org-wide.",
            )
        dept_id = req.department_id
    else:
        if ctx.department_id is None:
            raise HTTPException(status_code=400, detail="HOD account is not linked to a department.")
        dept_id = ctx.department_id
    summary = await perf_service.get_performance_summary(
        db, ctx, department_id=dept_id
    )
    return await generate_insight(summary, req)


@ai_router.post("/student-insight/{student_id}", response_model=StudentInsightOut)
async def student_insight(
    student_id: int,
    body: StudentInsightRequest | None = None,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission("VIEW_REPORTS", "VIEW_ALL_STUDENTS", "VIEW_DEPARTMENT_STUDENTS")
    ),
) -> StudentInsightOut:
    """Deep AI coaching brief for one student (TPO or HOD in scope)."""
    req = body or StudentInsightRequest()
    card = await perf_service.get_student_scorecard(db, ctx, student_id)
    scope = "department" if not ctx.sees_all_students else "organization"

    dept_context = None
    if req.include_dept_context and card.department_id is not None:
        summary = await perf_service.get_performance_summary(
            db, ctx, department_id=card.department_id
        )
        dept_context = next(
            (d for d in summary.by_department if d.id == card.department_id),
            None,
        )

    return await generate_student_insight(
        card,
        req,
        organization_id=ctx.organization_id,
        scope=scope,
        dept_context=dept_context,
    )
