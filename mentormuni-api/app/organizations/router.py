"""
Organization routes (MentorMuni platform + TPO reads).

POST /organizations
GET  /organizations
GET  /organizations/{id}
PUT  /organizations/{id}
POST /organizations/{id}/subscriptions
GET  /organizations/{id}/subscriptions
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_active_user, get_db, require_api_key
from app.models.user import User
from app.organizations import service as org_service
from app.organizations.schemas import (
    AssignSubscriptionRequest,
    OrganizationCreate,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationSubscriptionResponse,
    OrganizationUpdate,
)

router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
    dependencies=[Depends(require_api_key)],
)


def _sub_to_response(sub) -> OrganizationSubscriptionResponse:
    return OrganizationSubscriptionResponse(
        id=sub.id,
        organization_id=sub.organization_id,
        plan_id=sub.plan_id,
        plan_name=sub.plan.plan_name if getattr(sub, "plan", None) else None,
        start_date=sub.start_date,
        end_date=sub.end_date,
        student_limit=sub.student_limit,
        status=sub.status,
        created_at=sub.created_at,
    )


@router.post("", response_model=OrganizationResponse, status_code=201)
async def create_organization(
    body: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """MentorMuni platform: create a college (or public) tenant. API key only."""
    try:
        org = await org_service.create_organization(
            db,
            name=body.name,
            code=body.code,
            organization_type=body.organization_type,
            contact_person=body.contact_person,
            contact_email=str(body.contact_email) if body.contact_email else None,
            contact_phone=body.contact_phone,
            address=body.address,
            city=body.city,
            state=body.state,
            country=body.country,
            plan_id=body.plan_id,
            subscription_start_date=body.subscription_start_date,
        )
    except org_service.OrgError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return OrganizationResponse.model_validate(org)


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    organization_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> OrganizationListResponse:
    items, total = await org_service.list_organizations(
        db,
        organization_type=organization_type,
        status=status,
    )
    return OrganizationListResponse(
        items=[OrganizationResponse.model_validate(o) for o in items],
        total=total,
    )


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> OrganizationResponse:
    if user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Cannot access another organization.")
    try:
        org = await org_service.get_organization(db, organization_id)
    except org_service.OrgError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return OrganizationResponse.model_validate(org)


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    body: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    """Platform / ops update. Protected by API key (MentorMuni team)."""
    try:
        org = await org_service.update_organization(
            db,
            organization_id,
            **body.model_dump(exclude_unset=True),
        )
    except org_service.OrgError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return OrganizationResponse.model_validate(org)


@router.post(
    "/{organization_id}/subscriptions",
    response_model=OrganizationSubscriptionResponse,
    status_code=201,
)
async def assign_subscription(
    organization_id: int,
    body: AssignSubscriptionRequest,
    db: AsyncSession = Depends(get_db),
) -> OrganizationSubscriptionResponse:
    """Assign / upgrade / renew a plan for an organization."""
    try:
        sub = await org_service.assign_subscription(
            db,
            organization_id=organization_id,
            plan_id=body.plan_id,
            start_date=body.start_date,
            student_limit=body.student_limit,
        )
        # Reload with plan for response name.
        subs = await org_service.list_subscriptions(db, organization_id)
        sub = next(s for s in subs if s.id == sub.id)
    except org_service.OrgError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _sub_to_response(sub)


@router.get(
    "/{organization_id}/subscriptions",
    response_model=list[OrganizationSubscriptionResponse],
)
async def list_subscriptions(
    organization_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> list[OrganizationSubscriptionResponse]:
    if user.organization_id != organization_id:
        raise HTTPException(status_code=403, detail="Cannot access another organization.")
    try:
        subs = await org_service.list_subscriptions(db, organization_id)
    except org_service.OrgError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return [_sub_to_response(s) for s in subs]
