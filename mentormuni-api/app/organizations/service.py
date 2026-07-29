"""Organization + subscription assignment service."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.organization_access import (
    OrganizationAccessError,
    reject_suspend_if_public,
)
from app.models.enums import (
    OrganizationStatus,
    OrganizationType,
    PlanStatus,
    SubscriptionStatus,
)
from app.models.organization import Organization
from app.models.organization_subscription import OrganizationSubscription
from app.models.subscription_plan import SubscriptionPlan


class OrgError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _add_months(start: date, months: int) -> date:
    """Add calendar months without an extra dependency."""
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = start.day
    for candidate in (day, 30, 29, 28):
        try:
            return date(year, month, candidate)
        except ValueError:
            continue
    return date(year, month, 1)


async def create_organization(
    db: AsyncSession,
    *,
    name: str,
    code: str,
    organization_type: str,
    contact_person: str | None = None,
    contact_email: str | None = None,
    contact_phone: str | None = None,
    address: str | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    plan_id: int | None = None,
    subscription_start_date: date | None = None,
) -> Organization:
    code_norm = code.strip().upper()
    existing = await db.execute(select(Organization).where(Organization.code == code_norm))
    if existing.scalar_one_or_none():
        raise OrgError(f"Organization code '{code_norm}' already exists.", status_code=409)

    if organization_type not in {OrganizationType.COLLEGE.value, OrganizationType.PUBLIC.value}:
        raise OrgError("organization_type must be COLLEGE or PUBLIC.")

    org = Organization(
        name=name.strip(),
        code=code_norm,
        organization_type=organization_type,
        status=OrganizationStatus.ACTIVE.value,
        contact_person=contact_person,
        contact_email=str(contact_email).lower() if contact_email else None,
        contact_phone=contact_phone,
        address=address,
        city=city,
        state=state,
        country=country,
    )
    db.add(org)
    await db.flush()

    if plan_id is not None:
        await assign_subscription(
            db,
            organization_id=org.id,
            plan_id=plan_id,
            start_date=subscription_start_date,
        )

    await db.refresh(org)
    return org


async def get_organization(db: AsyncSession, organization_id: int) -> Organization:
    org = await db.get(Organization, organization_id)
    if org is None:
        raise OrgError("Organization not found.", status_code=404)
    return org


async def list_organizations(
    db: AsyncSession,
    *,
    organization_type: str | None = None,
    status: str | None = None,
) -> tuple[list[Organization], int]:
    stmt = select(Organization)
    count_stmt = select(func.count()).select_from(Organization)

    if organization_type:
        stmt = stmt.where(Organization.organization_type == organization_type)
        count_stmt = count_stmt.where(Organization.organization_type == organization_type)
    if status:
        stmt = stmt.where(Organization.status == status)
        count_stmt = count_stmt.where(Organization.status == status)

    stmt = stmt.order_by(Organization.id.asc())
    items = list((await db.execute(stmt)).scalars().all())
    total = int((await db.execute(count_stmt)).scalar_one())
    return items, total


async def update_organization(
    db: AsyncSession,
    organization_id: int,
    **fields: object,
) -> Organization:
    org = await get_organization(db, organization_id)
    incoming_status = fields.get("status")
    if isinstance(incoming_status, str) or incoming_status is None:
        try:
            reject_suspend_if_public(
                organization=org,
                incoming_status=incoming_status if isinstance(incoming_status, str) else None,
            )
        except OrganizationAccessError as exc:
            raise OrgError(exc.message, status_code=exc.status_code) from exc

    for key, value in fields.items():
        if value is None:
            continue
        if key == "contact_email" and value is not None:
            value = str(value).lower()
        setattr(org, key, value)
    await db.flush()
    await db.refresh(org)
    return org


async def assign_subscription(
    db: AsyncSession,
    *,
    organization_id: int,
    plan_id: int,
    start_date: date | None = None,
    student_limit: int | None = None,
) -> OrganizationSubscription:
    org = await get_organization(db, organization_id)
    plan = await db.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise OrgError("Subscription plan not found.", status_code=404)
    if plan.status != PlanStatus.ACTIVE.value:
        raise OrgError("Subscription plan is not ACTIVE.")

    active = await db.execute(
        select(OrganizationSubscription).where(
            OrganizationSubscription.organization_id == organization_id,
            OrganizationSubscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    for row in active.scalars().all():
        row.status = SubscriptionStatus.EXPIRED.value

    start = start_date or date.today()
    end = _add_months(start, plan.duration_months)
    limit = student_limit or plan.max_students

    sub = OrganizationSubscription(
        organization_id=org.id,
        plan_id=plan.id,
        plan_name=plan.plan_name,
        start_date=start,
        end_date=end,
        student_limit=limit,
        used_students=0,
        status=SubscriptionStatus.ACTIVE.value,
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def list_subscriptions(
    db: AsyncSession,
    organization_id: int,
) -> list[OrganizationSubscription]:
    await get_organization(db, organization_id)
    result = await db.execute(
        select(OrganizationSubscription)
        .where(OrganizationSubscription.organization_id == organization_id)
        .options(selectinload(OrganizationSubscription.plan))
        .order_by(OrganizationSubscription.id.desc())
    )
    return list(result.scalars().all())


async def list_plans(
    db: AsyncSession,
    *,
    plan_type: str | None = None,
) -> list[SubscriptionPlan]:
    stmt = select(SubscriptionPlan).where(SubscriptionPlan.status == PlanStatus.ACTIVE.value)
    if plan_type:
        stmt = stmt.where(SubscriptionPlan.plan_type == plan_type)
    stmt = stmt.order_by(SubscriptionPlan.id.asc())
    return list((await db.execute(stmt)).scalars().all())
