"""GET /dashboard — Identity funnel for Org Portal."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.dashboard import service as dashboard_service
from app.dashboard.schemas import DashboardIdentityResponse

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=DashboardIdentityResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(
        require_permission(
            "VIEW_REPORTS",
            "VIEW_ALL_STUDENTS",
            "VIEW_DEPARTMENT_STUDENTS",
            "VIEW_SELF_DASHBOARD",
        )
    ),
) -> DashboardIdentityResponse:
    return await dashboard_service.get_identity_dashboard(db, ctx)
