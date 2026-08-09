"""Organization performance analytics routes (TPO campus / HOD department)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.org_performance import service as perf_service
from app.org_performance.insight import generate_insight
from app.org_performance.schemas import (
    InsightOut,
    InsightRequest,
    PerformanceSummaryOut,
    ScorecardListOut,
)

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
