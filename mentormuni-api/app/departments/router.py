"""
Department routes (TPO / CREATE_DEPARTMENT).

POST   /departments
GET    /departments
PUT    /departments/{id}
DELETE /departments/{id}   (soft-delete)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.authz import require_permission
from app.common.deps import get_db, require_api_key
from app.common.tenant.context import TenantContext
from app.common.tenant.deps import get_tenant_context
from app.departments import service as dept_service
from app.departments.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate

router = APIRouter(
    prefix="/departments",
    tags=["Departments"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_DEPARTMENT")),
) -> DepartmentResponse:
    # Never trust organization_id from client — always JWT tenant.
    if body.organization_id is not None and body.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Cannot create department in another org.")
    try:
        dept = await dept_service.create_department(
            db,
            organization_id=ctx.organization_id,
            name=body.name,
            code=body.code,
        )
    except dept_service.DepartmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DepartmentResponse.model_validate(dept)


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> list[DepartmentResponse]:
    items = await dept_service.list_departments(db, organization_id=ctx.organization_id)
    return [DepartmentResponse.model_validate(d) for d in items]


@router.get("/{department_id}", response_model=DepartmentResponse)
async def get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
) -> DepartmentResponse:
    try:
        dept = await dept_service.get_department(db, department_id)
    except dept_service.DepartmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    if dept.organization_id != ctx.organization_id:
        raise HTTPException(status_code=403, detail="Department not in your organization.")
    return DepartmentResponse.model_validate(dept)


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_DEPARTMENT")),
) -> DepartmentResponse:
    try:
        dept = await dept_service.get_department(db, department_id)
        if dept.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Department not in your organization.")
        dept = await dept_service.update_department(
            db,
            department_id,
            **body.model_dump(exclude_unset=True),
        )
    except dept_service.DepartmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DepartmentResponse.model_validate(dept)


@router.delete("/{department_id}", response_model=DepartmentResponse)
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    ctx: TenantContext = Depends(require_permission("CREATE_DEPARTMENT")),
) -> DepartmentResponse:
    try:
        dept = await dept_service.get_department(db, department_id)
        if dept.organization_id != ctx.organization_id:
            raise HTTPException(status_code=403, detail="Department not in your organization.")
        dept = await dept_service.soft_delete_department(db, department_id)
    except dept_service.DepartmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DepartmentResponse.model_validate(dept)
