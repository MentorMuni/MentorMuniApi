"""Identity funnel dashboard service."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.tenant.context import TenantContext
from app.dashboard.schemas import DashboardIdentityResponse, DepartmentFunnelRow
from app.models.department import Department
from app.models.enums import RoleCode, UserStatus
from app.models.role import Role
from app.models.user import User


def _menu_for_role(role: str) -> list[str]:
    if role == RoleCode.ORG_ADMIN.value:
        return [
            "Dashboard",
            "Departments",
            "Department Heads",
            "Students",
            "Notifications",
            "Settings",
        ]
    if role == RoleCode.DEPARTMENT_ADMIN.value:
        return ["Dashboard", "Students", "Notifications", "Profile"]
    return ["Dashboard", "Notifications", "Profile"]


async def get_identity_dashboard(
    db: AsyncSession,
    ctx: TenantContext,
) -> DashboardIdentityResponse:
    org_id = ctx.organization_id
    scope = "organization"
    dept_scope_id: int | None = None
    menu = _menu_for_role(ctx.role)

    if ctx.sees_all_students:
        scope = "organization"
    elif "VIEW_DEPARTMENT_STUDENTS" in ctx.permissions and ctx.department_id is not None:
        scope = "department"
        dept_scope_id = ctx.department_id
    else:
        scope = "self"
        return DashboardIdentityResponse(
            organization_id=org_id,
            role=ctx.role,
            scope=scope,
            menu=menu,
            departments_total=0,
            departments_without_hod=0,
            hods_total=0,
            students_total=1 if ctx.role == RoleCode.STUDENT.value else 0,
            students_pending=0,
            students_active=1 if ctx.user.status == UserStatus.ACTIVE.value else 0,
            students_rejected=0,
            students_blocked=0,
            by_department=[],
            department_id=ctx.department_id,
        )

    dept_stmt = (
        select(Department)
        .where(Department.organization_id == org_id)
        .where(Department.deleted_at.is_(None))
        .order_by(Department.name.asc())
    )
    if dept_scope_id is not None:
        dept_stmt = dept_stmt.where(Department.id == dept_scope_id)

    departments = list((await db.execute(dept_stmt)).scalars().all())

    # Counts by role+status (+department)
    count_stmt = (
        select(
            User.department_id,
            Role.role_code,
            User.status,
            func.count().label("cnt"),
        )
        .join(Role, User.role_id == Role.id)
        .where(User.organization_id == org_id)
        .where(User.deleted_at.is_(None))
        .group_by(User.department_id, Role.role_code, User.status)
    )
    if dept_scope_id is not None:
        count_stmt = count_stmt.where(User.department_id == dept_scope_id)

    rows = (await db.execute(count_stmt)).all()

    # Aggregate helpers
    def _get(dept_id: int | None, role: str, status: str) -> int:
        for r in rows:
            if r.department_id == dept_id and r.role_code == role and r.status == status:
                return int(r.cnt)
        return 0

    def _sum_role(role: str, status: str | None = None, dept_id: int | None = ...) -> int:
        total = 0
        for r in rows:
            if r.role_code != role:
                continue
            if status is not None and r.status != status:
                continue
            if dept_id is not ... and r.department_id != dept_id:
                continue
            total += int(r.cnt)
        return total

    by_department: list[DepartmentFunnelRow] = []
    departments_without_hod = 0
    for d in departments:
        hod_count = (
            _get(d.id, RoleCode.DEPARTMENT_ADMIN.value, UserStatus.ACTIVE.value)
            + _get(d.id, RoleCode.DEPARTMENT_ADMIN.value, UserStatus.INVITED.value)
        )
        if hod_count == 0:
            departments_without_hod += 1
        pending = _get(d.id, RoleCode.STUDENT.value, UserStatus.PENDING.value)
        active = _get(d.id, RoleCode.STUDENT.value, UserStatus.ACTIVE.value)
        rejected = _get(d.id, RoleCode.STUDENT.value, UserStatus.REJECTED.value)
        blocked = _get(d.id, RoleCode.STUDENT.value, UserStatus.BLOCKED.value)
        by_department.append(
            DepartmentFunnelRow(
                department_id=d.id,
                department_code=d.code,
                department_name=d.name,
                students_total=pending + active + rejected + blocked,
                students_pending=pending,
                students_active=active,
                students_rejected=rejected,
                students_blocked=blocked,
                hod_count=hod_count,
                has_hod=hod_count > 0,
            )
        )

    students_pending = _sum_role(RoleCode.STUDENT.value, UserStatus.PENDING.value)
    students_active = _sum_role(RoleCode.STUDENT.value, UserStatus.ACTIVE.value)
    students_rejected = _sum_role(RoleCode.STUDENT.value, UserStatus.REJECTED.value)
    students_blocked = _sum_role(RoleCode.STUDENT.value, UserStatus.BLOCKED.value)

    return DashboardIdentityResponse(
        organization_id=org_id,
        role=ctx.role,
        scope=scope,
        menu=menu,
        departments_total=len(departments),
        departments_without_hod=departments_without_hod,
        hods_total=_sum_role(RoleCode.DEPARTMENT_ADMIN.value),
        students_total=students_pending
        + students_active
        + students_rejected
        + students_blocked,
        students_pending=students_pending,
        students_active=students_active,
        students_rejected=students_rejected,
        students_blocked=students_blocked,
        by_department=by_department,
        department_id=dept_scope_id,
    )
