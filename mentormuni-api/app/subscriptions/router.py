"""
Subscription plan catalog (read-only for frontend).

GET /subscription-plans

Auth: X-API-Key required. Bearer JWT not required.
Use returned ``id`` / ``plan_code`` — never hardcode plan IDs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.organizations import service as org_service
from app.organizations.schemas import SubscriptionPlanResponse

router = APIRouter(
    prefix="/subscription-plans",
    tags=["Subscription Plans"],
    dependencies=[Depends(require_api_key)],
)


@router.get(
    "",
    response_model=list[SubscriptionPlanResponse],
    summary="List subscription plans",
    description=(
        "Requires X-API-Key only. Canonical plan_code values: "
        "STARTER, GROWTH, ENTERPRISE, PREMIUM_STUDENT."
    ),
)
async def list_subscription_plans(
    plan_type: str | None = Query(default=None, description="COLLEGE or INDIVIDUAL"),
    db: AsyncSession = Depends(get_db),
) -> list[SubscriptionPlanResponse]:
    plans = await org_service.list_plans(db, plan_type=plan_type)
    return [SubscriptionPlanResponse.model_validate(p) for p in plans]
