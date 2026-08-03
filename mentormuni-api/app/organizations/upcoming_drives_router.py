"""
Upcoming placement drives — Org Admins (TPO / Dean / Director) only.

GET    /organizations/upcoming-drives
POST   /organizations/upcoming-drives
PUT    /organizations/upcoming-drives/{id}
DELETE /organizations/upcoming-drives/{id}

Shared across Org Admins in the same college. HODs cannot access.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context
from app.organizations import upcoming_drives_service as svc
from app.organizations.upcoming_drives_schemas import (
    UpcomingDriveCreate,
    UpcomingDriveListResponse,
    UpcomingDriveResponse,
    UpcomingDriveUpdate,
)

router = APIRouter(
    prefix="/organizations/upcoming-drives",
    tags=["Org Upcoming Drives"],
    dependencies=[Depends(require_api_key)],
)


def _to_response(drive) -> UpcomingDriveResponse:
    return UpcomingDriveResponse.model_validate(drive)


@router.get("", response_model=UpcomingDriveListResponse)
async def list_upcoming_drives(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> UpcomingDriveListResponse:
    try:
        items = await svc.list_drives(db, ctx=ctx)
    except svc.UpcomingDriveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return UpcomingDriveListResponse(items=[_to_response(i) for i in items])


@router.post("", response_model=UpcomingDriveResponse, status_code=201)
async def create_upcoming_drive(
    body: UpcomingDriveCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> UpcomingDriveResponse:
    try:
        drive = await svc.create_drive(
            db,
            ctx=ctx,
            company_name=body.company_name,
            eligibility_criteria=body.eligibility_criteria,
            drive_date=body.drive_date,
            remark=body.remark,
        )
    except svc.UpcomingDriveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(drive)


@router.put("/{drive_id}", response_model=UpcomingDriveResponse)
async def update_upcoming_drive(
    drive_id: int,
    body: UpcomingDriveUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> UpcomingDriveResponse:
    data = body.model_dump(exclude_unset=True)
    clear_remark = "remark" in data and data.get("remark") is None
    try:
        drive = await svc.update_drive(
            db,
            ctx=ctx,
            drive_id=drive_id,
            company_name=data.get("company_name"),
            eligibility_criteria=data.get("eligibility_criteria"),
            drive_date=data.get("drive_date"),
            remark=data.get("remark"),
            clear_remark=clear_remark,
        )
    except svc.UpcomingDriveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_response(drive)


@router.delete("/{drive_id}", status_code=204)
async def delete_upcoming_drive(
    drive_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> Response:
    try:
        await svc.delete_drive(db, ctx=ctx, drive_id=drive_id)
    except svc.UpcomingDriveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return Response(status_code=204)
