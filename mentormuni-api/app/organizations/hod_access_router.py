"""
HOD access policy — TPO configures what department mentors may do.

GET /organizations/hod-access
PUT /organizations/hod-access
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context
from app.organizations import hod_access_service as svc
from app.organizations.hod_access_schemas import HodAccessResponse, HodAccessUpdate

router = APIRouter(
    prefix="/organizations/hod-access",
    tags=["Org HOD Access"],
    dependencies=[Depends(require_api_key)],
)


@router.get("", response_model=HodAccessResponse)
async def get_hod_access(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> HodAccessResponse:
    try:
        return await svc.get_hod_access(db, ctx=ctx)
    except svc.HodAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.put("", response_model=HodAccessResponse)
async def update_hod_access(
    body: HodAccessUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> HodAccessResponse:
    try:
        return await svc.update_hod_access(db, ctx=ctx, body=body)
    except svc.HodAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
