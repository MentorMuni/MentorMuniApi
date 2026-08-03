"""Upcoming placement drives — shared across Org Admins in the college."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant.context import TenantContext
from app.models.enums import RoleCode
from app.models.upcoming_drive import UpcomingDrive


class UpcomingDriveError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def require_org_admin(ctx: TenantContext) -> None:
    """TPO / Dean / Director only (not HOD)."""
    if ctx.role == RoleCode.ORG_ADMIN.value or ctx.sees_all_students:
        return
    raise UpcomingDriveError(
        "Only Org Admins (TPO / Dean / Director) can manage upcoming drives.",
        status_code=403,
    )


async def list_drives(db: AsyncSession, *, ctx: TenantContext) -> list[UpcomingDrive]:
    require_org_admin(ctx)
    result = await db.execute(
        select(UpcomingDrive)
        .where(UpcomingDrive.organization_id == ctx.organization_id)
        .where(UpcomingDrive.deleted_at.is_(None))
        .order_by(UpcomingDrive.drive_date.asc(), UpcomingDrive.id.desc())
    )
    return list(result.scalars().all())


async def create_drive(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    company_name: str,
    eligibility_criteria: str,
    drive_date: date,
    remark: str | None = None,
) -> UpcomingDrive:
    require_org_admin(ctx)
    drive = UpcomingDrive(
        organization_id=ctx.organization_id,
        created_by=ctx.user_id,
        company_name=company_name.strip(),
        eligibility_criteria=eligibility_criteria.strip(),
        drive_date=drive_date,
        remark=(remark.strip() if remark else None) or None,
    )
    db.add(drive)
    await db.flush()
    await db.refresh(drive)
    return drive


async def get_org_drive(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    drive_id: int,
) -> UpcomingDrive:
    require_org_admin(ctx)
    result = await db.execute(
        select(UpcomingDrive)
        .where(UpcomingDrive.id == drive_id)
        .where(UpcomingDrive.organization_id == ctx.organization_id)
        .where(UpcomingDrive.deleted_at.is_(None))
    )
    drive = result.scalar_one_or_none()
    if drive is None:
        raise UpcomingDriveError("Upcoming drive not found.", status_code=404)
    return drive


async def update_drive(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    drive_id: int,
    company_name: str | None = None,
    eligibility_criteria: str | None = None,
    drive_date: date | None = None,
    remark: str | None = None,
    clear_remark: bool = False,
) -> UpcomingDrive:
    drive = await get_org_drive(db, ctx=ctx, drive_id=drive_id)
    if company_name is not None:
        drive.company_name = company_name.strip()
    if eligibility_criteria is not None:
        drive.eligibility_criteria = eligibility_criteria.strip()
    if drive_date is not None:
        drive.drive_date = drive_date
    if clear_remark:
        drive.remark = None
    elif remark is not None:
        drive.remark = remark.strip() or None
    drive.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(drive)
    return drive


async def delete_drive(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    drive_id: int,
) -> None:
    drive = await get_org_drive(db, ctx=ctx, drive_id=drive_id)
    drive.deleted_at = datetime.now(timezone.utc)
    drive.updated_at = datetime.now(timezone.utc)
    await db.flush()
