"""
Department routes (TPO).

POST /departments
GET  /departments
PUT  /departments/{id}
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_active_user, get_db, require_api_key, require_roles
from app.departments import service as dept_service
from app.departments.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate
from app.models.enums import RoleCode
from app.models.user import User

router = APIRouter(
    prefix="/departments",
    tags=["Departments"],
    dependencies=[Depends(require_api_key)],
)


@router.post("", response_model=DepartmentResponse, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.ORG_ADMIN.value)),
) -> DepartmentResponse:
    org_id = body.organization_id or user.organization_id
    if org_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Cannot create department in another org.")
    try:
        dept = await dept_service.create_department(
            db,
            organization_id=org_id,
            name=body.name,
            code=body.code,
        )
    except dept_service.DepartmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DepartmentResponse.model_validate(dept)


@router.get("", response_model=list[DepartmentResponse])
async def list_departments(
    organization_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
) -> list[DepartmentResponse]:
    org_id = organization_id or user.organization_id
    if org_id != user.organization_id:
        raise HTTPException(status_code=403, detail="Cannot list departments of another org.")
    items = await dept_service.list_departments(db, organization_id=org_id)
    return [DepartmentResponse.model_validate(d) for d in items]


@router.put("/{department_id}", response_model=DepartmentResponse)
async def update_department(
    department_id: int,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles(RoleCode.ORG_ADMIN.value)),
) -> DepartmentResponse:
    try:
        dept = await dept_service.get_department(db, department_id)
        if dept.organization_id != user.organization_id:
            raise HTTPException(status_code=403, detail="Department not in your organization.")
        dept = await dept_service.update_department(
            db,
            department_id,
            **body.model_dump(exclude_unset=True),
        )
    except dept_service.DepartmentError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return DepartmentResponse.model_validate(dept)
