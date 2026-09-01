"""Load and apply per-organization HOD access policy."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security.auth_errors import FORBIDDEN_ROLE, raise_forbidden
from app.common.tenant.context import TenantContext
from app.models.enums import RoleCode
from app.models.organization_hod_access import OrganizationHodAccess
from app.organizations.hod_access_schemas import HodAccessPolicy, HodAccessResponse, HodAccessUpdate

# Maps UI toggles → RBAC permission codes removed when toggle is off.
_TOGGLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "can_invite_students": ("UPLOAD_STUDENTS", "APPROVE_STUDENT"),
    "can_view_all_scores": (
        "VIEW_REPORTS",
        "VIEW_DEPARTMENT_STUDENTS",
        "EXPORT_REPORT",
    ),
    "can_assign_programs": ("ASSIGN_PROGRAM", "CREATE_COMPETITION"),
    "can_notify_department": ("SEND_NOTIFICATION",),
    "can_run_mocks": ("ASSIGN_ASSESSMENT",),
}

_STAFF_ROLES = frozenset(
    {
        RoleCode.ORG_ADMIN.value,
        RoleCode.DEPARTMENT_ADMIN.value,
    }
)


class HodAccessError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def default_policy_dict() -> dict[str, bool]:
    return HodAccessPolicy().model_dump()


def row_to_policy(row: OrganizationHodAccess | None) -> dict[str, bool]:
    if row is None:
        return default_policy_dict()
    return {
        "can_invite_students": bool(row.can_invite_students),
        "can_view_all_scores": bool(row.can_view_all_scores),
        "can_assign_programs": bool(row.can_assign_programs),
        "can_notify_department": bool(row.can_notify_department),
        "can_run_mocks": bool(row.can_run_mocks),
    }


def row_to_response(row: OrganizationHodAccess | None, *, organization_id: int) -> HodAccessResponse:
    policy = row_to_policy(row)
    return HodAccessResponse(
        organization_id=organization_id,
        updated_at=row.updated_at if row else None,
        **policy,
    )


def filter_permissions_for_hod(
    permissions: frozenset[str],
    policy: dict[str, bool],
) -> frozenset[str]:
    result = set(permissions)
    for toggle, codes in _TOGGLE_PERMISSIONS.items():
        if policy.get(toggle, True):
            continue
        for code in codes:
            result.discard(code)
    return frozenset(result)


async def get_hod_access_row(
    db: AsyncSession,
    organization_id: int,
) -> OrganizationHodAccess | None:
    result = await db.execute(
        select(OrganizationHodAccess).where(
            OrganizationHodAccess.organization_id == organization_id
        )
    )
    return result.scalar_one_or_none()


async def get_hod_access_policy(
    db: AsyncSession,
    organization_id: int,
) -> dict[str, bool]:
    row = await get_hod_access_row(db, organization_id)
    return row_to_policy(row)


def require_hod_access_reader(ctx: TenantContext) -> None:
    if ctx.role in _STAFF_ROLES:
        return
    raise_forbidden(
        code=FORBIDDEN_ROLE,
        message="Only campus staff can view HOD access settings.",
    )


def require_hod_access_writer(ctx: TenantContext) -> None:
    if ctx.role == RoleCode.ORG_ADMIN.value or ctx.sees_all_students:
        return
    raise_forbidden(
        code=FORBIDDEN_ROLE,
        message="Only TPO / Org Admins can change HOD access settings.",
    )


async def get_hod_access(
    db: AsyncSession,
    *,
    ctx: TenantContext,
) -> HodAccessResponse:
    require_hod_access_reader(ctx)
    if ctx.organization_id is None:
        raise HodAccessError("Organization context is required.", status_code=403)
    row = await get_hod_access_row(db, ctx.organization_id)
    return row_to_response(row, organization_id=ctx.organization_id)


async def update_hod_access(
    db: AsyncSession,
    *,
    ctx: TenantContext,
    body: HodAccessUpdate,
) -> HodAccessResponse:
    require_hod_access_writer(ctx)
    if ctx.organization_id is None:
        raise HodAccessError("Organization context is required.", status_code=403)

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HodAccessError("At least one HOD access field is required.", status_code=400)

    row = await get_hod_access_row(db, ctx.organization_id)
    if row is None:
        row = OrganizationHodAccess(organization_id=ctx.organization_id)
        db.add(row)

    for key, value in patch.items():
        setattr(row, key, bool(value))

    await db.flush()
    await db.refresh(row)
    return row_to_response(row, organization_id=ctx.organization_id)
