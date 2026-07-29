"""Department service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.organization_access import (
    OrganizationAccessError,
    ensure_organization_active,
)
from app.models.department import Department
from app.models.enums import DepartmentStatus, OrganizationType
from app.models.organization import Organization


class DepartmentError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


async def create_department(
    db: AsyncSession,
    *,
    organization_id: int,
    name: str,
    code: str,
) -> Department:
    org = await db.get(Organization, organization_id)
    if org is None:
        raise DepartmentError("Organization not found.", status_code=404)
    if org.organization_type != OrganizationType.COLLEGE.value:
        raise DepartmentError("Only COLLEGE organizations can have departments.")
    try:
        ensure_organization_active(org)
    except OrganizationAccessError as exc:
        raise DepartmentError(exc.message, status_code=exc.status_code) from exc

    code_norm = code.strip().upper()
    existing = await db.execute(
        select(Department).where(
            Department.organization_id == organization_id,
            Department.code == code_norm,
        )
    )
    if existing.scalar_one_or_none():
        raise DepartmentError(
            f"Department code '{code_norm}' already exists in this organization.",
            status_code=409,
        )

    dept = Department(
        organization_id=organization_id,
        name=name.strip(),
        code=code_norm,
        status=DepartmentStatus.ACTIVE.value,
    )
    db.add(dept)
    await db.flush()
    await db.refresh(dept)
    return dept


async def list_departments(
    db: AsyncSession,
    *,
    organization_id: int,
) -> list[Department]:
    result = await db.execute(
        select(Department)
        .where(Department.organization_id == organization_id)
        .order_by(Department.name.asc())
    )
    return list(result.scalars().all())


async def get_department(db: AsyncSession, department_id: int) -> Department:
    dept = await db.get(Department, department_id)
    if dept is None:
        raise DepartmentError("Department not found.", status_code=404)
    return dept


async def update_department(
    db: AsyncSession,
    department_id: int,
    **fields: object,
) -> Department:
    dept = await get_department(db, department_id)
    for key, value in fields.items():
        if value is None:
            continue
        setattr(dept, key, value)
    await db.flush()
    await db.refresh(dept)
    return dept
